"""Run complete development Compose with ephemeral credentials and real collection."""
import hashlib
import json
import os
import pathlib
import secrets
import subprocess
import tempfile
import time

ROOT=pathlib.Path(__file__).resolve().parents[2]
COMPOSE=[str(ROOT/'.deps/docker-compose-s07'),'-p','nexstream-s07-stack','-f',str(ROOT/'nexstream-deploy/docker-compose.sprint07.yml')]
with tempfile.TemporaryDirectory(prefix='nexstream-s07-compose-') as folder:
    directory=pathlib.Path(folder);env=os.environ.copy()
    def run(args,**kwargs):return subprocess.run(args,env=env,check=True,capture_output=True,text=True,timeout=120,**kwargs).stdout
    def fixture(name,value,variable):
        path=directory/name;path.write_text(value);path.chmod(0o644);env[variable]=str(path)
    password=secrets.token_hex(24);api=secrets.token_hex(32);salt=secrets.token_bytes(16)
    fixture('pg-password',password,'NEXSTREAM_POSTGRES_PASSWORD_FILE')
    fixture('pgpass','postgres:5432:nexstream:nexstream_admin:'+password+'\n','NEXSTREAM_POSTGRES_PGPASS_FILE')
    fixture('ch-password',secrets.token_hex(24),'NEXSTREAM_CLICKHOUSE_PASSWORD_FILE')
    fixture('api-secret',api,'NEXSTREAM_AGENT_SECRET_FILE')
    run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(directory/'key'),'-out',str(directory/'cert'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'])
    fixture('server.pem',(directory/'cert').read_text()+(directory/'key').read_text(),'NEXSTREAM_TLS_SERVER_PEM')
    env['NEXSTREAM_AGENT_CA_FILE']=str(directory/'cert');(directory/'cert').chmod(0o644)
    try:
        run(COMPOSE+['config','-q'])
        run(COMPOSE+['up','-d','--scale','processor='+env.get('NEXSTREAM_COMPOSE_PROCESSORS','1')])
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try:
                run(COMPOSE+['exec','-T','postgres','psql','-U','nexstream_admin','-d','nexstream','-c','SELECT count(*) FROM agent_credentials'])
                break
            except subprocess.CalledProcessError:time.sleep(.5)
        verifier=hashlib.pbkdf2_hmac('sha256',api.encode(),salt,100000).hex()
        sql=f"""INSERT INTO agents(id,agent_id,host_id) VALUES ('77777777-7777-7777-7777-777777777777','dev-agent','dev-host');
INSERT INTO credential_change_events(key_id,event_type) VALUES ('dev-key','created');
INSERT INTO agent_credentials(key_id,agent_id,secret_salt,secret_verifier,iterations,not_before,expires_at,change_version)
VALUES ('dev-key','77777777-7777-7777-7777-777777777777',decode('{salt.hex()}','hex'),decode('{verifier}','hex'),100000,now()-interval '1 minute',now()+interval '1 hour',1);"""
        run(COMPOSE+['exec','-T','postgres','psql','-U','nexstream_admin','-d','nexstream','-v','ON_ERROR_STOP=1'],input=sql)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try:
                result=run(COMPOSE+['exec','-T','query','bash','-c',"exec 3<>/dev/tcp/127.0.0.1/8080; printf 'GET /v1/hosts/dev-host/latest HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n' >&3; cat <&3"])
                body=json.loads(result.split('\r\n\r\n')[-1] if '\r\n\r\n' in result else result.split('\n\n')[-1])
                if body.get('data'):
                    print('PASS full Compose Agent → TLS → Gateway → PostgreSQL → Kafka → ClickHouse → Query')
                    print(json.dumps(body));break
            except (subprocess.CalledProcessError,ValueError):pass
            time.sleep(1)
        else:
            print(run(COMPOSE+['logs','--tail','40','agent','query','nexstream-ingest','clickhouse']))
            raise AssertionError('Compose row not visible')
        print(run(COMPOSE+['ps']))
        workers=run(COMPOSE+['ps','--format','json','processor'])
        states=[json.loads(line) for line in workers.splitlines() if line.strip()]
        assert len(states)==int(env.get('NEXSTREAM_COMPOSE_PROCESSORS','1')) and all(state['State']=='running' for state in states)
        print('PASS live Processor instances:',len(states))
        for state in states:
            budget=json.loads(run(['docker','inspect','--format','{{json .HostConfig}}',state['Name']]))
            assert budget['Memory']==256*1024*1024 and budget['PidsLimit']==64
        print('PASS Processor container memory/pid budgets: 256 MiB / 64')
        run(COMPOSE+['run','--rm','bootstrap-topics'])
        print('PASS repeat topic bootstrap')
    finally:
        subprocess.run(COMPOSE+['down','--volumes','--remove-orphans'],env=env,capture_output=True,timeout=120)
