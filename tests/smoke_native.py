"""Test real local services using synthetic API responses and no real credentials."""
from pathlib import Path
import json
import os
import secrets
import shutil
import signal
import subprocess
import time
import requests

source = Path(__file__).resolve().parents[1]
state = Path('/tmp/oryth-native-test-' + secrets.token_hex(4))
project = state/'synthetic-project'
(project/'scripts').mkdir(parents=True)
shutil.copytree(source/'grafana', project/'grafana')
shutil.copytree(source/'prometheus', project/'prometheus')
shutil.copy(source/'scripts/monitor_common.py',project/'scripts/monitor_common.py')
for name in ['censys','xposedornot']:
    shutil.copy(source/'scripts'/f'{name}-monitor.py', project/'scripts'/f'_{name}.py')
    payload = {'result':{'resource':{'ip':'192.0.2.1','services':[{'port':80},{'port':443}]}}} if name=='censys' else {'breaches': [['SyntheticOne', 'SyntheticTwo']], 'status': 'success'}
    wrapper = '''import json
from pathlib import Path
import runpy
import requests

def synthetic_get(*args, **kwargs):
    response=requests.Response()
    response.status_code=200
    response._content=json.dumps(PAYLOAD).encode()
    return response
requests.get=synthetic_get
runpy.run_path(str(Path(__file__).with_name(ORIGINAL)), run_name='__main__')
'''.replace('PAYLOAD', repr(payload)).replace('ORIGINAL',repr('_'+name+'.py'))
    (project/'scripts'/f'{name}-monitor.py').write_text(wrapper)
password = secrets.token_urlsafe(24)
env = os.environ.copy()
# Explicit synthetic values prevent any user API keys or addresses from entering this test.
env.update(CENSYS_TOKEN='synthetic-unused-token', MY_PUBLIC_IP='192.0.2.1',
           CENSYS_ORGANIZATION_ID='',
           MY_EMAILS='first@example.invalid,second@example.invalid',
           GF_SECURITY_ADMIN_USER='oryth-test', GF_SECURITY_ADMIN_PASSWORD=password)
session=requests.Session()
session.auth=('oryth-test',password)
report={'mode':'synthetic API responses; real native services and HTTP', 'state_directory':str(state), 'checks':{}}
stream=(state/'launcher.log').open('w')
process=subprocess.Popen(['python3',str(source/'scripts/run-local.py'),'--project',str(project),'--state',str(state/'state')],
                         env=env,stdout=stream,stderr=subprocess.STDOUT)

def wait_get(url, auth=False):
    end=time.monotonic()+90
    while time.monotonic()<end:
        if process.poll() is not None:
            raise RuntimeError('Native launcher exited; inspect '+str(state/'launcher.log'))
        try:
            result=(session if auth else requests).get(url,timeout=3)
            if result.status_code==200:
                return result
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError('Endpoint not ready: '+url)

def query(expression):
    result=requests.get('http://127.0.0.1:9090/api/v1/query',params={'query':expression},timeout=10)
    result.raise_for_status()
    payload=result.json()
    assert payload['status']=='success',payload.get('errorType','query failure')
    return payload['data']['result']

try:
    for name,url in [('censys_metrics','http://127.0.0.1:8000/metrics'),
                     ('xposedornot_metrics','http://127.0.0.1:8001/metrics'),
                     ('prometheus_health','http://127.0.0.1:9090/-/ready'),
                     ('grafana_health','http://127.0.0.1:3000/api/health')]:
        result=wait_get(url)
        if name=='grafana_health':
            assert result.json()['database']=='ok'
        report['checks'][name]='PASS'
        print(name,'PASS',flush=True)
    promtool=shutil.which('promtool') or next((str(path) for path in Path('/tmp/oryth-native-runtime/prometheus').glob('*/promtool')), None)
    if not promtool:
        raise RuntimeError('Install promtool on PATH or alongside the native Prometheus runtime')
    checked=subprocess.run([str(promtool),'check','config',str(state/'state/prometheus.yml')],capture_output=True,text=True)
    assert checked.returncode==0,checked.stderr
    report['checks']['promtool_config']='PASS'
    end=time.monotonic()+45
    while time.monotonic()<end:
        targets=query('up')
        breaches=query('sum(xposedornot_breaches_total)')
        if len(targets)==2 and all(row['value'][1]=='1' for row in targets) and breaches and breaches[0]['value'][1]=='4':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Expected healthy targets and synthetic metrics did not arrive')
    assert query('censys_open_ports_total')[0]['value'][1]=='2'
    assert query('censys_services_total')[0]['value'][1]=='2'
    report['checks']['prometheus_targets']='PASS (2/2)'
    report['checks']['expected_metrics']='PASS (2 ports, 2 services, 4 total breaches across 2 synthetic emails)'
    print('expected_metrics PASS',flush=True)
    dashboard=wait_get('http://127.0.0.1:3000/api/dashboards/uid/oryth-cyber-risk',auth=True).json()['dashboard']
    report['checks']['dashboard_provisioning']='PASS'
    health=session.get('http://127.0.0.1:3000/api/datasources/uid/oryth-prometheus/health',timeout=15)
    health.raise_for_status()
    assert health.json()['status']=='OK'
    report['checks']['grafana_datasource']='PASS'
    page=session.get('http://127.0.0.1:3000/d/oryth-cyber-risk',timeout=10)
    page.raise_for_status()
    assert '<html' in page.text.lower()
    report['checks']['dashboard_page']='PASS'
    count=0
    now=int(time.time()*1000)
    for panel in dashboard['panels']:
        for target in panel['targets']:
            query(target['expr'])
            payload={'from':str(now-60000),'to':str(now),'queries':[dict(target,
                datasource={'type':'prometheus','uid':'oryth-prometheus'},intervalMs=15000,maxDataPoints=10)]}
            result=session.post('http://127.0.0.1:3000/api/ds/query',json=payload,timeout=15)
            result.raise_for_status()
            results=result.json()['results']
            assert all(not result.get('error') for result in results.values()),panel['title']
            count+=1
    report['checks']['dashboard_queries']=f'PASS ({count} through both Prometheus and Grafana)'
    print('dashboard_queries PASS',count,flush=True)
    report['checks']['runtime']='PASS'
except Exception as error:
    report['failure']=str(error)
    print('TEST FAILURE:',type(error).__name__,str(error),flush=True)
    raise
finally:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    stream.close()
    (state/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Report:',state/'report.json',flush=True)
