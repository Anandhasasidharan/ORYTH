"""Validate a running Compose stack, including every dashboard query."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def compose(*arguments):
    result = subprocess.run(['docker', 'compose', *arguments], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode:
        print(result.stderr.strip() or result.stdout.strip() or 'Docker command failed.', file=sys.stderr)
        raise RuntimeError('Stack validation failed')
    return result.stdout


def main():
    if not shutil.which('docker'):
        print('Docker CLI is unavailable. Install/start Docker Desktop or Docker Engine with Compose.', file=sys.stderr)
        return 2
    try:
        compose('config', '--quiet')
        compose('exec', '-T', 'prometheus', 'promtool', 'check', 'config', '/etc/prometheus/prometheus.yml')
        # Execute requests from inside the network; no additional public ports are needed.
        probe = '''
import json
import urllib.request

def get(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)

health = get('http://grafana:3000/api/health')
assert health.get('database') == 'ok', 'Grafana database is unavailable'
result = get('http://prometheus:9090/api/v1/query?query=up')
assert result['status'] == 'success', 'Prometheus query failed'
targets = {row['metric']['job']: row['value'][1] for row in result['data']['result']}
assert all(targets.get(job) == '1' for job in ('censys', 'xposedornot')), 'Exporter targets are not both up'
'''
        compose('exec', '-T', 'censys', 'python', '-c', probe)
        for path in (ROOT / 'grafana' / 'dashboards').glob('*.json'):
            dashboard = json.loads(path.read_text())
            for panel in dashboard['panels']:
                for target in panel.get('targets', []):
                    compose('exec', '-T', 'prometheus', 'promtool', 'query', 'instant',
                            'http://localhost:9090', target['expr'])
        print('PASS: Grafana database, Prometheus configuration, both exporter targets and all dashboard queries.')
        print('Check dashboard lookup status separately for live API credentials and permissions.')
        return 0
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
