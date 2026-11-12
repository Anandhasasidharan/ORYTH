"""Exercise real local services with synthetic data, including the packaged executable."""
import json
from pathlib import Path
import secrets
import tempfile
import time

import requests

from .services import DASHBOARD_URL, ServiceManager
from .settings import user_directory


def run(report_path=None, runtime=None):
    report_path = Path(report_path or Path(tempfile.gettempdir()) / 'oryth-self-test.json').resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    state = Path(tempfile.mkdtemp(prefix='oryth-smoke-user space-', dir=report_path.parent))
    manager = ServiceManager(state, runtime=runtime or user_directory() / 'runtime')
    password = secrets.token_urlsafe(24)
    settings = {'public_ip': '192.0.2.1', 'censys_token': 'synthetic-unused-token',
                'emails': ['first@example.invalid', 'second@example.invalid'], 'dashboard_password': password}
    report = {'mode': 'synthetic external API responses; real local services', 'checks': {}, 'state_directory': str(state)}
    session = requests.Session()
    session.auth = ('admin', password)
    def query(expression):
        result = requests.get('http://127.0.0.1:9090/api/v1/query', params={'query': expression}, timeout=10)
        result.raise_for_status()
        payload = result.json()
        assert payload['status'] == 'success'
        return payload['data']['result']
    try:
        manager.start(settings, synthetic=True)
        report['checks']['http_services'] = 'PASS (4/4)'
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            targets = query('up')
            breaches = query('sum(xposedornot_breaches_total)')
            if len(targets) == 2 and all(row['value'][1] == '1' for row in targets) and breaches and breaches[0]['value'][1] == '4':
                break
            manager.check_processes()
            time.sleep(0.5)
        else:
            raise RuntimeError('Expected metrics did not reach Prometheus.')
        assert query('censys_open_ports_total')[0]['value'][1] == '2'
        assert query('censys_services_total')[0]['value'][1] == '2'
        report['checks']['expected_metrics'] = 'PASS (2 ports, 2 services, 4 email breach matches)'
        response = session.get('http://127.0.0.1:3000/api/dashboards/uid/oryth-cyber-risk', timeout=10)
        response.raise_for_status()
        dashboard = response.json()['dashboard']
        response = session.get('http://127.0.0.1:3000/api/datasources/uid/oryth-prometheus/health', timeout=15)
        response.raise_for_status()
        assert response.json()['status'] == 'OK'
        page = session.get(DASHBOARD_URL, timeout=10)
        page.raise_for_status()
        assert '<html' in page.text.lower()
        report['checks']['grafana_dashboard_and_datasource'] = 'PASS'
        count = 0
        now = int(time.time() * 1000)
        for panel in dashboard['panels']:
            for target in panel['targets']:
                query(target['expr'])
                payload = {'from': str(now - 60000), 'to': str(now), 'queries': [dict(target,
                    datasource={'type': 'prometheus', 'uid': 'oryth-prometheus'}, intervalMs=15000, maxDataPoints=10)]}
                result = session.post('http://127.0.0.1:3000/api/ds/query', json=payload, timeout=15)
                result.raise_for_status()
                assert all(not item.get('error') for item in result.json()['results'].values()), panel['title']
                count += 1
        report['checks']['dashboard_queries'] = f'PASS ({count})'
        report['result'] = 'PASS'
        code = 0
    except Exception as error:
        report['result'] = 'FAIL'
        report['error'] = str(error)
        code = 1
    finally:
        manager.stop()
        session.close()
        report['checks']['cleanup'] = 'PASS' if not manager.processes else 'FAIL'
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if code == 0 and any(process for process in manager.processes.values()):
        return 1
    return code
