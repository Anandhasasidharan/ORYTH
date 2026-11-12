"""Start, check and stop the local monitoring services on Windows or Linux."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

import requests

from .runtime import check_cancel, ensure_runtime
from .settings import resource_root, validate_settings

DASHBOARD_URL = 'http://127.0.0.1:3000/d/oryth-cyber-risk'
PORTS = (8000, 8001, 9090, 3000)


def ensure_ports_available():
    for port in PORTS:
        with socket.socket() as probe:
            if os.name == 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                raise RuntimeError(f'Port {port} is in use. Close the other ORYTH instance or application and retry.') from None


def exporter_command(name, synthetic=False):
    if getattr(sys, 'frozen', False):
        command = [sys.executable, '--exporter', name]
    else:
        command = [sys.executable, str(resource_root() / 'oryth_app.py'), '--exporter', name]
    if synthetic:
        command.append('--synthetic')
    return command


class ServiceManager:
    def __init__(self, directory, runtime=None, root=None):
        self.directory = Path(directory).resolve()
        self.runtime = Path(runtime or self.directory / 'runtime').resolve()
        self.root = Path(root or resource_root()).resolve()
        self.processes = {}
        self.streams = []

    def prepare(self, settings):
        settings = validate_settings(settings)
        directory = self.directory
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'logs').mkdir(exist_ok=True)
        for kind in ('datasources', 'dashboards'):
            (directory / 'provisioning' / kind).mkdir(parents=True, exist_ok=True)
        source = self.root / 'grafana' / 'provisioning'
        datasource = (source / 'datasources/datasource.yml').read_text(encoding='utf-8')
        (directory / 'provisioning/datasources/datasource.yml').write_text(datasource, encoding='utf-8')
        dashboard = (source / 'dashboards/dashboard.yml').read_text(encoding='utf-8')
        dashboard_path = (self.root / 'grafana/dashboards').as_posix()
        dashboard = re.sub(r'(?m)^(\s*path:).*$', lambda match: match[1] + ' ' + json.dumps(dashboard_path), dashboard)
        (directory / 'provisioning/dashboards/dashboard.yml').write_text(dashboard, encoding='utf-8')
        (directory / 'prometheus.yml').write_text((self.root / 'prometheus/prometheus.yml').read_text(), encoding='utf-8')
        env = os.environ.copy()
        # Explicit values isolate each user configuration from shell variables and repo .env files.
        env.update(CENSYS_TOKEN=settings['censys_token'], MY_PUBLIC_IP=settings['public_ip'],
                   CENSYS_ORGANIZATION_ID=settings['organization_id'], MY_EMAILS=','.join(settings['emails']),
                   DATA_DIR=str(directory / 'snapshots'), PYTHONUNBUFFERED='1',
                   GF_PATHS_DATA=str(directory / 'grafana-data'), GF_PATHS_LOGS=str(directory / 'logs'),
                   GF_PATHS_PLUGINS=str(directory / 'plugins'), GF_PATHS_PROVISIONING=str(directory / 'provisioning'),
                   GF_SERVER_HTTP_ADDR='127.0.0.1', GF_SERVER_HTTP_PORT='3000',
                   GF_USERS_ALLOW_SIGN_UP='false', GF_SECURITY_ADMIN_USER='admin',
                   GF_SECURITY_ADMIN_PASSWORD=settings['dashboard_password'],
                   GF_ANALYTICS_REPORTING_ENABLED='false', GF_ANALYTICS_CHECK_FOR_UPDATES='false',
                   GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES='false', GF_PLUGINS_PREINSTALL_DISABLED='true',
                   GF_LOG_LEVEL='warn')
        return env

    def start(self, settings, progress=lambda message: None, cancel=None, synthetic=False, wait=True):
        if self.processes:
            raise RuntimeError('ORYTH is already running.')
        ensure_ports_available()
        binaries = ensure_runtime(self.runtime, progress, cancel)
        check_cancel(cancel)
        env = self.prepare(settings)
        grafana = binaries['grafana']
        grafana_home = grafana.parent.parent
        grafana_command = [str(grafana)]
        if grafana.stem != 'grafana-server':
            grafana_command.append('server')
        grafana_command.append('--homepath=' + str(grafana_home))
        commands = {
            'censys': exporter_command('censys', synthetic),
            'xposedornot': exporter_command('xposedornot', synthetic),
            'prometheus': [str(binaries['prometheus']), '--config.file=' + str(self.directory / 'prometheus.yml'),
                           '--storage.tsdb.path=' + str(self.directory / 'prometheus-data'),
                           '--storage.tsdb.retention.time=30d', '--web.listen-address=127.0.0.1:9090'],
            'grafana': grafana_command,
        }
        try:
            for name, command in commands.items():
                check_cancel(cancel)
                stream = (self.directory / 'logs' / f'{name}.log').open('a', encoding='utf-8')
                self.streams.append(stream)
                child_env = dict(env, ORYTH_SERVICE_LOG=str(self.directory / 'logs' / f'{name}.log'))
                options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                self.processes[name] = subprocess.Popen(command, cwd=self.root, env=child_env,
                                                        stdout=stream, stderr=subprocess.STDOUT, **options)
            if wait:
                self.wait_ready(progress, cancel)
        except BaseException:
            self.stop()
            raise

    def check_processes(self):
        for name, process in self.processes.items():
            if process.poll() is not None:
                raise RuntimeError(f'{name.title()} stopped. See {self.directory / "logs" / (name + ".log")} for details.')

    def wait_ready(self, progress=lambda message: None, cancel=None, timeout=120):
        progress('Starting your dashboard…')
        pending = {'http://127.0.0.1:8000/metrics', 'http://127.0.0.1:8001/metrics',
                   'http://127.0.0.1:9090/-/ready', 'http://127.0.0.1:3000/api/health'}
        deadline = time.monotonic() + timeout
        while pending and time.monotonic() < deadline:
            check_cancel(cancel)
            self.check_processes()
            for url in tuple(pending):
                try:
                    response = requests.get(url, timeout=1)
                    if response.status_code == 200:
                        if url.endswith('/api/health') and response.json().get('database') != 'ok':
                            continue
                        pending.remove(url)
                except (requests.RequestException, ValueError):
                    pass
            if pending:
                time.sleep(0.25)
        if pending:
            raise RuntimeError('Dashboard startup timed out. Open the logs folder for details.')
        progress('Monitoring is running. Your dashboard is ready.')

    def stop(self):
        for process in reversed(list(self.processes.values())):
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
        for process in reversed(list(self.processes.values())):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self.processes.clear()
        for stream in self.streams:
            stream.close()
        self.streams.clear()
