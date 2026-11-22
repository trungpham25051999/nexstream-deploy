"""All writes/TTL changes are confined to the dedicated S07H ClickHouse fixture."""
import json
import math
import pathlib
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
import uuid

EVIDENCE=pathlib.Path(__file__).resolve().parent/'results/2026-11-22-sprint-07-hardening'
def sql(query):
    request=urllib.request.Request('http://127.0.0.1:28123/?user=hardening_fixture',data=query.encode())
    with urllib.request.urlopen(request,timeout=15) as response:return response.read().decode(),dict(response.headers)
def scalar(query):return int(sql(query)[0].strip())
def rows(query):return [json.loads(line) for line in sql(query+' FORMAT JSONEachRow')[0].splitlines()]
def insert(records):
    sql('INSERT INTO nexstream.telemetry_raw FORMAT JSONEachRow\n'+'\n'.join(json.dumps(r) for r in records))
def wait(predicate):
    end=time.monotonic()+20
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.1)
    raise AssertionError('ingestion deadline')
def rpk(*args,input=None):return subprocess.run(['docker','exec','-i','nexstream-s07h-kafka','rpk',*args,'-X','brokers=redpanda:9092'],input=input,text=True,capture_output=True,check=True,timeout=20).stdout

tag=uuid.uuid4().hex[:12];base=int(time.time()*1000);host='identity-'+tag
record=dict(schema_version=1,host_id=host,message_id='same',sampled_at=base-60000,ingested_at=base,cpu_usage_percent=20,memory_used_bytes=20,memory_total_bytes=100)
# DateTime64 JSON numeric values are seconds by default; insert exact formatted UTC strings.
def stamp(ms):return time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(ms//1000))+'.'+str(ms%1000).zfill(3)
record.update(sampled_at=stamp(base-60000),ingested_at=stamp(base))
insert([record,{**record,'ingested_at':stamp(base+1000)},{**record,'ingested_at':stamp(base+2000),'sampled_at':stamp(base+5000),'cpu_usage_percent':99}])
actual=rows(f"SELECT * FROM nexstream.telemetry_deduplicated WHERE host_id='{host}'")
assert len(actual)==1 and actual[0]['cpu_usage_percent']==20
assert scalar(f"SELECT count() FROM nexstream.telemetry_deduplicated WHERE host_id='{host}' AND sampled_at>=fromUnixTimestamp64Milli({base+4999})")==0
insert([{**record,'message_id':'tie','cpu_usage_percent':90},{**record,'message_id':'tie','cpu_usage_percent':10}])
assert rows(f"SELECT cpu_usage_percent FROM nexstream.telemetry_deduplicated WHERE host_id='{host}' AND message_id='tie'")[0]['cpu_usage_percent']==10
print('PASS duplicate/conflicting identity: earliest ingestion wins; deterministic tie; time predicate sees canonical winner')

replay_host='replay-'+tag
event=dict(schema_version=1,host_id=replay_host,message_id='replayed',sample_timestamp_ms=base,cpu_usage_percent=40,memory_used_bytes=40,memory_total_bytes=100)
rpk('topic','produce','telemetry.events.v1','-p','0','-k',replay_host,input=(json.dumps(event)+'\n')*2)
wait(lambda:scalar(f"SELECT count() FROM nexstream.telemetry_raw WHERE host_id='{replay_host}'")==2)
rpk('topic','produce','telemetry.events.v1','-p','0','-k',replay_host,input=json.dumps({**event,'cpu_usage_percent':80})+'\n')
wait(lambda:scalar(f"SELECT count() FROM nexstream.telemetry_raw WHERE host_id='{replay_host}'")==3)
actual=rows(f"SELECT * FROM nexstream.telemetry_deduplicated WHERE host_id='{replay_host}'")
assert len(actual)==1 and actual[0]['cpu_usage_percent']==40
print('PASS real Kafka replay: three physical records remain one canonical identity')

before=sql('SHOW CREATE TABLE nexstream.telemetry_raw')[0]
sql('CREATE DATABASE IF NOT EXISTS nexstream_hardening_fixture')
ttl='nexstream_hardening_fixture.ttl_'+tag
sql(f'CREATE TABLE {ttl} (id UInt64, ts DateTime) ENGINE=MergeTree ORDER BY id TTL ts + INTERVAL 5 SECOND DELETE SETTINGS merge_with_ttl_timeout=1')
sql(f'INSERT INTO {ttl} VALUES (1,now()-60),(2,now()+3600)')
sql(f'ALTER TABLE {ttl} MATERIALIZE TTL SETTINGS mutations_sync=2')
assert [int(row['id']) for row in rows(f'SELECT id FROM {ttl}')]==[2]
assert sql('SHOW CREATE TABLE nexstream.telemetry_raw')[0]==before
print('PASS five-second fixture TTL removes expired row, retains live row; seven-day raw policy unchanged')

bench='benchmark-'+tag
sql(f"INSERT INTO nexstream.telemetry_raw SELECT 1,'{bench}',concat('m-',toString(number%50000)),fromUnixTimestamp64Milli({base}+toInt64(number%50000)),fromUnixTimestamp64Milli({base}+toInt64(number)),toFloat64(number%100),toUInt64(number%1000+1),toUInt64(10000) FROM numbers(100000)")
assert scalar(f"SELECT count() FROM nexstream.telemetry_raw WHERE host_id='{bench}'")==100000
assert scalar(f"SELECT count() FROM nexstream.telemetry_deduplicated WHERE host_id='{bench}'")==50000
measurements={}
for name,table in [('raw','telemetry_raw'),('deduplicated','telemetry_deduplicated')]:
    query=f"SELECT count(),sum(cpu_usage_percent),sum(memory_used_bytes) FROM nexstream.{table} WHERE host_id='{bench}'"
    for _ in range(2):sql(query)
    samples=[];summary={}
    for _ in range(20):
        start=time.perf_counter();_,headers=sql(query);samples.append((time.perf_counter()-start)*1000)
        summary=json.loads(headers.get('X-ClickHouse-Summary','{}'))
    ordered=sorted(samples)
    measurements[name]={'runs':20,'p50_ms':statistics.median(samples),'p95_ms':ordered[math.ceil(.95*len(ordered))-1],
                        'p99_ms':ordered[math.ceil(.99*len(ordered))-1],'summary_last':summary,'samples_ms':samples}
evidence={'fixture_host':bench,'raw_rows':100000,'logical_identities':50000,'warmup_runs':2,'client_concurrency':1,'measurements':measurements}
EVIDENCE.mkdir(parents=True,exist_ok=True);(EVIDENCE/'dedup-measurements.json').write_text(json.dumps(evidence,indent=2))
print('MEASURED bounded local dedup workload:',json.dumps(evidence))
print('PASS analytics correctness and fixture retention; fixture rows retained for review')
