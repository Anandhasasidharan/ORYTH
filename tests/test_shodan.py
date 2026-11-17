"""Shodan integration tests use synthetic responses and never a real API key."""
from functools import partial
import json
import math
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import prometheus_client
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from oryth.settings import validate_settings, save_settings, load_settings
from oryth.services import ServiceManager


@pytest.fixture
def monitor(monkeypatch):
    registry = prometheus_client.CollectorRegistry()
    monkeypatch.setattr(prometheus_client, 'Gauge', partial(prometheus_client.Gauge, registry=registry))
    namespace = runpy.run_path(str(ROOT / 'scripts/shodan-monitor.py'))
    return SimpleNamespace(**namespace), registry


def response(status=200, payload=None):
    return Mock(status_code=status, json=Mock(return_value=payload))


def test_shodan_success_exports_generic_metrics_and_saves_host(monitor, tmp_path):
    app, registry = monitor
    host = {'ip_str': '192.0.2.1', 'ports': [80, 443], 'data': [{'port': 80}, {'port': 443}, {'port': 443}]}
    get = Mock(return_value=response(payload=host))
    assert app.scan('private-test-key', '192.0.2.1', tmp_path, get=get)
    assert registry.get_sample_value('network_observed_ports') == 2
    assert registry.get_sample_value('network_observed_services') == 3
    assert registry.get_sample_value('shodan_open_ports_total') == 2
    assert registry.get_sample_value('network_lookup_success') == 1
    assert registry.get_sample_value('network_provider_info', {'provider': 'Shodan'}) == 1
    assert get.call_args.args[0] == 'https://api.shodan.io/shodan/host/192.0.2.1'
    assert get.call_args.kwargs['params'] == {'key': 'private-test-key', 'history': 'false', 'minify': 'false'}
    assert json.loads((tmp_path / 'shodan_latest.json').read_text()) == host


@pytest.mark.parametrize('status', [401, 403, 404, 429, 500])
def test_failed_shodan_lookup_is_unknown_and_preserves_snapshot(monitor, tmp_path, status):
    app, registry = monitor
    saved = tmp_path / 'shodan_latest.json'
    saved.write_text('{"previous":true}')
    assert not app.scan('private-test-key', '192.0.2.1', tmp_path, get=Mock(return_value=response(status)))
    assert math.isnan(registry.get_sample_value('network_observed_ports'))
    assert registry.get_sample_value('network_lookup_success') == 0
    assert json.loads(saved.read_text()) == {'previous': True}


@pytest.mark.parametrize('host', [
    {}, {'ip_str': '192.0.2.2', 'ports': [], 'data': []},
    {'ip_str': '192.0.2.1', 'ports': None, 'data': []},
    {'ip_str': '192.0.2.1', 'ports': [True], 'data': []},
    {'ip_str': '192.0.2.1', 'ports': [0], 'data': []},
    {'ip_str': '192.0.2.1', 'ports': [80], 'data': [None]},
    {'ip_str': '192.0.2.1', 'ports': [80], 'data': [{'port': 443}]},
    {'ip_str': '192.0.2.1', 'ports': [], 'data': None},
])
def test_shodan_malformed_response_does_not_become_clean(monitor, tmp_path, host):
    app, registry = monitor
    assert not app.scan('private-test-key', '192.0.2.1', tmp_path, get=Mock(return_value=response(payload=host)))
    assert registry.get_sample_value('network_lookup_success') == 0
    assert not list(tmp_path.iterdir())


def test_valid_shodan_empty_observations_are_zero(monitor, tmp_path):
    app, registry = monitor
    assert app.scan('private-test-key', '192.0.2.1', tmp_path,
                    get=Mock(return_value=response(payload={'ip_str': '192.0.2.1', 'ports': [], 'data': []})))
    assert registry.get_sample_value('network_observed_ports') == 0
    assert registry.get_sample_value('network_lookup_success') == 1


def test_shodan_never_logs_request_url_key_or_response_body(monitor, tmp_path, caplog):
    app, _ = monitor
    get = Mock(side_effect=requests.Timeout('https://api.shodan.io/?key=private-test-key'))
    assert not app.scan('private-test-key', '192.0.2.1', tmp_path, get=get)
    assert 'private-test-key' not in caplog.text
    assert 'https://' not in caplog.text
    get = Mock(return_value=response(403, {'error': 'private-test-key'}))
    assert not app.scan('private-test-key', '192.0.2.1', tmp_path, get=get)
    assert 'private-test-key' not in caplog.text


@pytest.mark.parametrize('configured', [True, False])
def test_shodan_startup_without_api_requests(monitor, tmp_path, monkeypatch, configured):
    app, registry = monitor
    namespace = app.main.__globals__
    server = Mock()
    scan = Mock()
    class EndCycle(Exception):
        pass
    def sleep(_):
        raise EndCycle
    monkeypatch.setitem(namespace, 'load_config', lambda: None)
    monkeypatch.setitem(namespace, 'start_http_server', server)
    monkeypatch.setitem(namespace, 'scan', scan)
    monkeypatch.setitem(namespace, 'time', SimpleNamespace(sleep=sleep))
    monkeypatch.setenv('SHODAN_API_KEY', 'synthetic-key' if configured else '')
    monkeypatch.setenv('MY_PUBLIC_IP', '192.0.2.1' if configured else '')
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    with pytest.raises(EndCycle):
        app.main()
    assert registry.get_sample_value('network_monitor_enabled') == int(configured)
    assert scan.call_count == int(configured)
    server.assert_called_once_with(8000, addr='127.0.0.1')


def test_existing_censys_settings_keep_their_provider(tmp_path):
    previous = {'public_ip': '192.0.2.1', 'censys_token': 'synthetic-censys-token',
                'emails': [], 'dashboard_password': 'local-password'}
    (tmp_path / 'settings.json').write_text(json.dumps(previous))
    settings = load_settings(tmp_path)
    assert settings['network_provider'] == 'censys'
    assert settings['shodan_api_key'] == ''
    assert settings['censys_token'] == previous['censys_token']


def test_shodan_settings_survive_round_trip(tmp_path):
    settings = save_settings(tmp_path, {'network_provider': 'shodan', 'public_ip': '192.0.2.1',
                              'shodan_api_key': 'synthetic-shodan-key'})
    assert load_settings(tmp_path) == settings


@pytest.mark.parametrize('values', [
    {'network_provider': 'unknown'},
    {'network_provider': 'shodan', 'public_ip': '192.0.2.1'},
    {'network_provider': 'shodan', 'shodan_api_key': 'synthetic-key'},
])
def test_invalid_provider_settings_are_rejected(values):
    with pytest.raises(ValueError):
        validate_settings(values)


@pytest.mark.parametrize('provider', ['shodan', 'censys'])
def test_only_selected_provider_key_is_passed_to_workers(tmp_path, provider):
    env = ServiceManager(tmp_path).prepare({'network_provider': provider, 'public_ip': '192.0.2.1',
          'shodan_api_key': 'synthetic-shodan-key', 'censys_token': 'synthetic-censys-token'})
    assert env['SHODAN_API_KEY'] == ('synthetic-shodan-key' if provider == 'shodan' else '')
    assert env['CENSYS_TOKEN'] == ('synthetic-censys-token' if provider == 'censys' else '')
