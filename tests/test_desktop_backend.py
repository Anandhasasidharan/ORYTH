import hashlib
import io
import json
from pathlib import Path
import sys
import threading
from unittest.mock import Mock
import zipfile

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oryth import runtime
from oryth.services import ServiceManager, ensure_ports_available, exporter_command
from oryth.settings import load_settings, save_settings, validate_settings


def test_settings_round_trip_deduplicates_and_keeps_dashboard_password(tmp_path):
    settings = save_settings(tmp_path, {'emails': 'First@Example.com\nsecond@example.com,first@example.com'})
    assert settings['emails'] == ['first@example.com', 'second@example.com']
    assert len(settings['dashboard_password']) >= 24
    assert load_settings(tmp_path) == settings
    assert not (tmp_path / 'settings.json.tmp').exists()


@pytest.mark.parametrize('settings', [
    {'public_ip': '192.0.2.1'}, {'censys_token': 'token'},
    {'public_ip': 'bad-ip', 'censys_token': 'token'}, {'emails': 'invalid'},
    {'emails': [None]}, {'emails': [f'p{i}@example.com' for i in range(101)]},
])
def test_settings_reject_invalid_configuration(settings):
    with pytest.raises(ValueError):
        validate_settings(settings)


def test_blank_settings_support_free_email_only_mode():
    settings = validate_settings({'emails': 'person@example.com'})
    assert settings['censys_token'] == ''
    assert settings['public_ip'] == ''
    assert settings['emails'] == ['person@example.com']


def test_windows_downloads_are_official_and_use_zip_archives():
    for name in ('grafana', 'prometheus'):
        filename, url, checksum = runtime.artifact(name, 'windows')
        assert filename.endswith('.windows-amd64.zip')
        assert url.startswith(('https://dl.grafana.com/', 'https://github.com/prometheus/prometheus/'))
        assert checksum.startswith('https://')


def test_checksum_rejects_tampered_download_before_extraction(tmp_path):
    path = tmp_path / 'runtime.zip'
    path.write_bytes(b'original')
    checksum = hashlib.sha256(b'original').hexdigest()
    assert runtime.verify_archive(path, checksum + '  runtime.zip', 'runtime.zip') == checksum
    path.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='checksum failed'):
        runtime.verify_archive(path, checksum + '  runtime.zip', 'runtime.zip')


@pytest.mark.parametrize('entry', ['../escape.exe', '/absolute.exe', 'C:/absolute.exe', '..\\escape.exe'])
def test_zip_extraction_rejects_unsafe_paths(tmp_path, entry):
    path = tmp_path / 'runtime.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(entry, 'bad')
    with pytest.raises(ValueError, match='Unsafe path'):
        runtime.extract_archive(path, tmp_path / 'unpacked')
    assert not (tmp_path / 'escape.exe').exists()


def test_zip_extraction_rejects_symbolic_links(tmp_path):
    path = tmp_path / 'runtime.zip'
    entry = zipfile.ZipInfo('link')
    entry.create_system = 3
    entry.external_attr = 0o120777 << 16
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(entry, '../outside')
    with pytest.raises(ValueError):
        runtime.extract_archive(path, tmp_path / 'unpacked')


def test_cancelled_setup_does_not_download(tmp_path, monkeypatch):
    cancel = threading.Event()
    cancel.set()
    get = Mock()
    monkeypatch.setattr(runtime.requests, 'get', get)
    with pytest.raises(runtime.SetupCancelled):
        runtime.ensure_runtime(tmp_path, cancel=cancel)
    get.assert_not_called()


def test_runtime_download_verifies_and_installs_both_components(tmp_path, monkeypatch):
    archives = {}
    for name in ('grafana', 'prometheus'):
        stream = io.BytesIO()
        executable = 'bin/grafana' if name == 'grafana' else 'prometheus'
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr(executable, 'synthetic executable')
        archives[name] = stream.getvalue()
    def get(url, **kwargs):
        name = 'prometheus' if 'prometheus' in url else 'grafana'
        filename, _, checksum_url = runtime.artifact(name)
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.headers = {'Content-Length': str(len(archives[name]))}
        response.iter_content.return_value = [archives[name]]
        if url == checksum_url:
            response.text = hashlib.sha256(archives[name]).hexdigest() + '  ' + filename
        return response
    monkeypatch.setattr(runtime.requests, 'get', get)
    monkeypatch.setattr(runtime, 'find_binary', lambda directory, name, system=None:
        next((p for p in Path(directory).rglob(name) if p.is_file()), None))
    binaries = runtime.ensure_runtime(tmp_path)
    assert set(binaries) == {'prometheus', 'grafana'}
    for name, binary in binaries.items():
        assert binary.exists()
        assert json.loads((tmp_path / name / '.oryth-runtime.json').read_text())['version'] == runtime.VERSIONS[name]


def test_packaged_exporter_launches_same_exe_without_python_installation(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    assert exporter_command('xposedornot') == [sys.executable, '--exporter', 'xposedornot']


def test_process_environment_clears_inherited_credentials_and_quotes_paths(tmp_path, monkeypatch):
    monkeypatch.setenv('CENSYS_TOKEN', 'inherited-sensitive-token')
    monkeypatch.setenv('MY_EMAILS', 'inherited@example.com')
    state = tmp_path / 'Example User' / 'Application Data'
    manager = ServiceManager(state)
    env = manager.prepare({'emails': ['person@example.com'], 'dashboard_password': 'local-password'})
    assert env['CENSYS_TOKEN'] == ''
    assert env['MY_EMAILS'] == 'person@example.com'
    assert env['GF_SERVER_HTTP_ADDR'] == '127.0.0.1'
    data = yaml.safe_load((state / 'provisioning/dashboards/dashboard.yml').read_text())
    assert data['providers'][0]['options']['path'].endswith('/grafana/dashboards')
    assert env['GF_PATHS_DATA'] == str(state / 'grafana-data')


def test_start_failure_stops_already_started_children(tmp_path, monkeypatch):
    import oryth.services as services
    monkeypatch.setattr(services, 'ensure_ports_available', lambda: None)
    monkeypatch.setattr(services, 'ensure_runtime', lambda *args:
        {'prometheus': Path('/fake/prometheus'), 'grafana': Path('/fake/bin/grafana')})
    child = Mock()
    child.poll.return_value = None
    spawn = Mock(side_effect=[child, OSError('simulated launch failure')])
    monkeypatch.setattr(services.subprocess, 'Popen', spawn)
    manager = ServiceManager(tmp_path)
    with pytest.raises(OSError):
        manager.start({'emails': []})
    child.terminate.assert_called_once()
    child.wait.assert_called_once()
    assert not manager.processes
    assert not manager.streams


def test_port_conflict_has_actionable_message(monkeypatch):
    import oryth.services as services
    probe = Mock()
    probe.__enter__ = Mock(return_value=probe)
    probe.__exit__ = Mock(return_value=None)
    probe.bind.side_effect = OSError('busy')
    monkeypatch.setattr(services.socket, 'socket', Mock(return_value=probe))
    with pytest.raises(RuntimeError, match='Port 8000 is in use'):
        ensure_ports_available()
