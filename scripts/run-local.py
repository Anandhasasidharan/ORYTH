"""Run ORYTH directly in WSL/Linux using native Prometheus and Grafana binaries."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--runtime', type=Path, default=Path('/tmp/oryth-native-runtime'))
    parser.add_argument('--state', type=Path, default=Path('/tmp/oryth-local-state'))
    args = parser.parse_args()
    root = args.project.resolve()
    runtime = args.runtime.resolve()
    state = args.state.resolve()
    prometheus = shutil.which('prometheus') or next((str(p) for p in runtime.glob('prometheus/*/prometheus') if p.is_file()), None)
    grafana = shutil.which('grafana') or next((str(p) for p in runtime.glob('grafana/*/bin/grafana') if p.is_file()), None)
    if not prometheus or not grafana:
        parser.error('Native prometheus and grafana binaries are required on PATH or under --runtime.')
    grafana_home = Path(os.environ.get('GRAFANA_HOME', str(Path(grafana).resolve().parents[1])))
    state.mkdir(parents=True, exist_ok=True)
    (state / 'logs').mkdir(exist_ok=True)
    provision = state / 'provisioning'
    for kind in ('datasources', 'dashboards'):
        (provision / kind).mkdir(parents=True, exist_ok=True)
    source = root / 'grafana' / 'provisioning'
    datasource = (source / 'datasources/datasource.yml').read_text().replace('http://prometheus:9090', 'http://127.0.0.1:9090')
    (provision / 'datasources/datasource.yml').write_text(datasource)
    dashboard = (source / 'dashboards/dashboard.yml').read_text().replace('/var/lib/grafana/dashboards', str(root / 'grafana/dashboards'))
    (provision / 'dashboards/dashboard.yml').write_text(dashboard)
    prometheus_config = (root / 'prometheus/prometheus.yml').read_text().replace('censys:8000', '127.0.0.1:8000').replace('xposedornot:8001', '127.0.0.1:8001')
    (state / 'prometheus.yml').write_text(prometheus_config)
    load_dotenv(root / '.env')
    env = os.environ.copy()
    env['DATA_DIR'] = str(state / 'snapshots')
    env['PYTHONUNBUFFERED'] = '1'
    settings = {
        'GF_PATHS_DATA': str(state / 'grafana-data'),
        'GF_PATHS_LOGS': str(state / 'logs'),
        'GF_PATHS_PLUGINS': str(state / 'plugins'),
        'GF_PATHS_PROVISIONING': str(provision),
        'GF_SERVER_HTTP_ADDR': '127.0.0.1',
        'GF_SERVER_HTTP_PORT': '3000',
        'GF_USERS_ALLOW_SIGN_UP': 'false',
        'GF_SECURITY_ADMIN_USER': env.get('GRAFANA_ADMIN_USER', 'admin'),
        'GF_SECURITY_ADMIN_PASSWORD': env.get('GRAFANA_ADMIN_PASSWORD', 'admin'),
        'GF_ANALYTICS_REPORTING_ENABLED': 'false',
        'GF_ANALYTICS_CHECK_FOR_UPDATES': 'false',
        'GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES': 'false',
        'GF_PLUGINS_PREINSTALL_DISABLED': 'true',
    }
    for key, value in settings.items():
        env.setdefault(key, value)
    commands = [
        ('censys', [sys.executable, str(root / 'scripts/censys-monitor.py')]),
        ('xposedornot', [sys.executable, str(root / 'scripts/xposedornot-monitor.py')]),
        ('prometheus', [prometheus, '--config.file=' + str(state / 'prometheus.yml'),
                        '--storage.tsdb.path=' + str(state / 'prometheus-data'),
                        '--web.listen-address=127.0.0.1:9090']),
        ('grafana', [grafana, 'server', '--homepath=' + str(grafana_home)]),
    ]
    processes = []
    streams = []
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for name, command in commands:
            stream = (state / 'logs' / f'{name}.log').open('a')
            streams.append(stream)
            processes.append((name, subprocess.Popen(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)))
        print('ORYTH started without Docker. Grafana: http://127.0.0.1:3000/d/oryth-cyber-risk', flush=True)
        print(f'Logs and local data: {state}', flush=True)
        print('Press Ctrl+C to stop all four processes.', flush=True)
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    raise RuntimeError(f'{name} exited with status {process.returncode}; see {state}/logs/{name}.log')
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1
    finally:
        for _, process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for _, process in reversed(processes):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in streams:
            stream.close()


if __name__ == '__main__':
    sys.exit(main())
