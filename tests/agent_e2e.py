"""Runtime-only local secrets/certificate fixture. Needs existing S07 Kafka/CH/Query."""
import hashlib
import json
import pathlib
import secrets
import subprocess
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30, **kwargs).stdout

with tempfile.TemporaryDirectory(prefix='nexstream-s07-e2e-') as folder:
    directory = pathlib.Path(folder)
    processes = []
    containers = []
    host = 'agent-' + secrets.token_hex(6)
    try:
        run(['docker','run','-d','--name','nexstream-s07-pg','-p','127.0.0.1:15432:5432',
             '-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_DB=nexstream',
             '-v',str(ROOT/'nexstream-deploy/postgres/migrations')+':/docker-entrypoint-initdb.d:ro',
             'postgres:16-bookworm'])
        containers.append('nexstream-s07-pg')
        for _ in range(100):
            result = subprocess.run(['docker','exec','nexstream-s07-pg','pg_isready','-U','postgres'],capture_output=True)
            if result.returncode == 0: break
            time.sleep(.1)
        time.sleep(1)
        secret = secrets.token_hex(32); salt = secrets.token_bytes(16)
        verifier = hashlib.pbkdf2_hmac('sha256', secret.encode(), salt, 100000).hex()
        (directory/'secret').write_text(secret)
        sql = f"""INSERT INTO agents(id,agent_id,host_id) VALUES ('77777777-7777-7777-7777-777777777777','s07-agent','{host}');
INSERT INTO credential_change_events(key_id,event_type) VALUES ('s07-key','created');
INSERT INTO agent_credentials(key_id,agent_id,secret_salt,secret_verifier,iterations,not_before,expires_at,change_version)
VALUES ('s07-key','77777777-7777-7777-7777-777777777777',decode('{salt.hex()}','hex'),decode('{verifier}','hex'),100000,now()-interval '1 minute',now()+interval '1 hour',1);"""
        run(['docker','exec','-i','nexstream-s07-pg','psql','-U','postgres','-d','nexstream','-v','ON_ERROR_STOP=1'],input=sql)
        run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(directory/'key'),
             '-out',str(directory/'cert'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'])
        (directory/'server.pem').write_bytes((directory/'cert').read_bytes()+(directory/'key').read_bytes())
        config = (ROOT/'nexstream-deploy/haproxy/haproxy.cfg').read_text().replace('/run/secrets/nexstream_server.pem','/fixture/server.pem').replace('nexstream-ingest:9000','127.0.0.1:9000')
        (directory/'haproxy.cfg').write_text(config)
        gateway = subprocess.Popen([str(ROOT/'nexstream-ingest/build-s05-pg/nexstream-ingest'),'--port','9000','--kafka-bootstrap','127.0.0.1:19092','--postgres','host=127.0.0.1 port=15432 dbname=nexstream user=postgres'],stdout=subprocess.DEVNULL)
        processes.append(gateway)
        run(['docker','run','-d','--name','nexstream-s07-haproxy','--user','0','--network','host',
             '-v',folder+':/fixture:ro','haproxy:2.9.12-alpine','haproxy','-f','/fixture/haproxy.cfg'])
        containers.append('nexstream-s07-haproxy'); time.sleep(2)
        agent = subprocess.Popen([str(ROOT/'nexstream-publisher/build-s06/nexstream-agent'),
            '--address','127.0.0.1','--port','9443','--tls-hostname','localhost','--ca-file',str(directory/'cert'),
            '--queue-db',str(directory/'queue.sqlite'),'--agent-id','s07-agent','--host-id',host,
            '--key-id','s07-key','--secret-file',str(directory/'secret')],stdout=subprocess.DEVNULL)
        processes.append(agent)
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            with urllib.request.urlopen('http://127.0.0.1:8080/v1/hosts/'+host+'/latest',timeout=5) as response:
                rows=json.load(response)['data']
            if rows:
                assert rows[0]['memory_total_bytes']>0
                print('PASS Agent TLS → HAProxy → PG-authenticated Gateway → Kafka → ClickHouse → Query')
                print(json.dumps(rows[0])); break
            time.sleep(.5)
        else: raise AssertionError('no real Agent row visible')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate(); process.wait(timeout=15)
        for name in reversed(containers):
            subprocess.run(['docker','rm','-f',name],capture_output=True)
