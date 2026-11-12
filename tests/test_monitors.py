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


@pytest.fixture
def load_monitor(monkeypatch):
    gauge = prometheus_client.Gauge

    def load(name):
        registry = prometheus_client.CollectorRegistry()
        monkeypatch.setattr(prometheus_client, 'Gauge', partial(gauge, registry=registry))
        namespace = runpy.run_path(str(ROOT / 'scripts' / f'{name}-monitor.py'))
        return SimpleNamespace(**namespace), registry
    return load


def value(registry, name, labels=None):
    return registry.get_sample_value(name, labels or {})


def response(status=200, payload=None, headers=None):
    return Mock(status_code=status, json=Mock(return_value=payload), headers=headers or {})


def test_censys_current_schema_and_persistence(load_monitor, tmp_path):
    monitor, registry = load_monitor('censys')
    host = {'ip': '192.0.2.1', 'services': [
        {'port': 443, 'transport_protocol': 'tcp'},
        {'port': 443, 'transport_protocol': 'udp'}, {'port': 80}]}
    get = Mock(return_value=response(payload={'result': {'resource': host}}))
    assert monitor.scan('secret', '192.0.2.1', tmp_path, 'org-id', get=get)
    assert json.loads((tmp_path / 'censys_latest.json').read_text()) == host
    assert value(registry, 'censys_open_ports_total') == 2
    assert value(registry, 'censys_services_total') == 3
    assert value(registry, 'censys_scrape_success') == 1
    assert value(registry, 'censys_last_success_timestamp_seconds') > 0
    assert get.call_args.kwargs['params'] == {'organization_id': 'org-id'}
    assert get.call_args.kwargs['headers']['Authorization'] == 'Bearer secret'


@pytest.mark.parametrize('status', [401, 403, 404, 429, 500])
def test_censys_errors_do_not_report_clean_result(load_monitor, tmp_path, status):
    monitor, registry = load_monitor('censys')
    saved = tmp_path / 'censys_latest.json'
    saved.write_text('{"previous": true}')
    assert not monitor.scan('secret', '192.0.2.1', tmp_path,
                            get=Mock(return_value=response(status)))
    assert math.isnan(value(registry, 'censys_open_ports_total'))
    assert value(registry, 'censys_scrape_success') == 0
    assert json.loads(saved.read_text()) == {'previous': True}


@pytest.mark.parametrize('payload', [{}, {'result': {'host': {}}},
    {'result': {'resource': {'services': None}}},
    {'result': {'resource': {'services': [{'port': '443'}]}}}])
def test_censys_malformed_response(load_monitor, tmp_path, payload):
    monitor, registry = load_monitor('censys')
    assert not monitor.scan('secret', '192.0.2.1', tmp_path,
                            get=Mock(return_value=response(payload=payload)))
    assert math.isnan(value(registry, 'censys_services_total'))
    assert not list(tmp_path.iterdir())


def test_censys_valid_empty_services(load_monitor, tmp_path):
    monitor, registry = load_monitor('censys')
    assert monitor.scan('secret', '192.0.2.1', tmp_path,
                        get=Mock(return_value=response(payload={'result': {'resource': {'services': []}}})))
    assert value(registry, 'censys_open_ports_total') == 0
    assert value(registry, 'censys_scrape_success') == 1


def test_xposedornot_success_names_and_encoded_email(load_monitor, tmp_path):
    monitor, registry = load_monitor('xposedornot')
    email = 'person+tag@example.com'
    get = Mock(return_value=response(payload={'breaches': [['Example', 'Other', 'Example']], 'status': 'success'}))
    assert monitor.check_email(email, tmp_path, get=get) == 1
    assert get.call_args.args[0] == 'https://api.xposedornot.com/v1/check-email/person%2Btag%40example.com'
    assert 'hibp-api-key' not in get.call_args.kwargs['headers']
    assert 'Authorization' not in get.call_args.kwargs['headers']
    assert value(registry, 'xposedornot_breaches_total', {'email': email}) == 2
    assert value(registry, 'xposedornot_scrape_success', {'email': email}) == 1
    saved = json.loads(next(tmp_path.glob('xposedornot_*.json')).read_text())
    assert saved['breaches'] == ['Example', 'Other']
    assert saved['provider'] == 'XposedOrNot'


@pytest.mark.parametrize('status', [200, 404])
def test_xposedornot_explicit_no_match_is_valid_zero(load_monitor, tmp_path, status):
    monitor, registry = load_monitor('xposedornot')
    monitor.check_email('person@example.com', tmp_path,
        get=Mock(return_value=response(status, payload={'Error': 'Not found', 'email': None})))
    assert value(registry, 'xposedornot_breaches_total', {'email': 'person@example.com'}) == 0
    assert value(registry, 'xposedornot_scrape_success', {'email': 'person@example.com'}) == 1


@pytest.mark.parametrize('status', [401, 403, 429, 500])
def test_xposedornot_failure_invalidates_previous_success(load_monitor, tmp_path, status):
    monitor, registry = load_monitor('xposedornot')
    email = 'person@example.com'
    monitor.check_email(email, tmp_path, get=Mock(return_value=response(404, payload={'Error': 'Not found'})))
    old_result = next(tmp_path.glob('*.json')).read_text()
    monitor.check_email(email, tmp_path, get=Mock(return_value=response(status)))
    assert math.isnan(value(registry, 'xposedornot_breaches_total', {'email': email}))
    assert value(registry, 'xposedornot_scrape_success', {'email': email}) == 0
    assert next(tmp_path.glob('*.json')).read_text() == old_result


@pytest.mark.parametrize('retry, expected', [('120', 120), ('bad', 3600), ('NaN', 3600), ('-1', 1), (None, 3600)])
def test_xposedornot_rate_limit_backoff(load_monitor, tmp_path, retry, expected):
    monitor, _ = load_monitor('xposedornot')
    assert monitor.check_email('person@example.com', tmp_path,
        get=Mock(return_value=response(429, headers={'Retry-After': retry}))) == expected


@pytest.mark.parametrize('payload', [{}, [None], {'breaches': ['FlatName']},
    {'breaches': [[None]]}, {'breaches': [['']]}, {'Error': 'Server error'},
    {'Error': 'Server error', 'breaches': []}, {'breaches': [], 'status': 'error'}])
def test_xposedornot_malformed_response(load_monitor, tmp_path, payload):
    monitor, registry = load_monitor('xposedornot')
    monitor.check_email('person@example.com', tmp_path,
                        get=Mock(return_value=response(payload=payload)))
    assert value(registry, 'xposedornot_scrape_success', {'email': 'person@example.com'}) == 0
    assert not list(tmp_path.iterdir())


def test_xposedornot_unexpected_404_does_not_report_zero(load_monitor, tmp_path):
    monitor, registry = load_monitor('xposedornot')
    monitor.check_email('person@example.com', tmp_path,
        get=Mock(return_value=response(404, payload={'message': 'Route not found'})))
    assert value(registry, 'xposedornot_scrape_success', {'email': 'person@example.com'}) == 0
    assert math.isnan(value(registry, 'xposedornot_breaches_total', {'email': 'person@example.com'}))


def test_xposedornot_same_localpart_different_domains(load_monitor, tmp_path):
    monitor, _ = load_monitor('xposedornot')
    for email in ['same@example.com', 'same@example.org', '../../unsafe@example.com']:
        monitor.check_email(email, tmp_path, get=Mock(return_value=response(404, payload={'Error': 'Not found'})))
    assert len(list(tmp_path.glob('xposedornot_*.json'))) == 3


def test_xposedornot_hourly_limit_spreads_large_batches(load_monitor, monkeypatch, tmp_path):
    monitor, _ = load_monitor('xposedornot')
    now = [0.0]
    called_at = []
    def check(email, data_dir):
        called_at.append(now[0])
        return 1.0
    def sleep(delay):
        now[0] += delay
    monkeypatch.setitem(monitor.poll_emails.__globals__, 'check_email', check)
    monitor.poll_emails([f'person{i}@example.com' for i in range(26)], tmp_path,
                       sleep=sleep, clock=lambda: now[0])
    assert len(called_at) == 26
    assert called_at[24] == 24
    assert called_at[25] >= 3600


@pytest.mark.parametrize('name', ['censys', 'xposedornot'])
def test_network_timeouts_do_not_crash(load_monitor, tmp_path, name, caplog):
    monitor, _ = load_monitor(name)
    get = Mock(side_effect=requests.Timeout('secret-token-and-email'))
    if name == 'censys':
        assert not monitor.scan('secret', '192.0.2.1', tmp_path, get=get)
    else:
        monitor.check_email('person@example.com', tmp_path, get=get)
    assert 'secret-token-and-email' not in caplog.text


def test_atomic_write_preserves_previous_result_on_failure(tmp_path):
    from monitor_common import write_json
    path = tmp_path / 'result.json'
    write_json(path, {'valid': True})
    with pytest.raises(ValueError):
        write_json(path, {'invalid': math.nan})
    assert json.loads(path.read_text()) == {'valid': True}
    assert list(tmp_path.iterdir()) == [path]


class EndCycle(Exception):
    pass


def end_cycle(_):
    raise EndCycle


@pytest.mark.parametrize('name, configured', [('censys', False), ('xposedornot', False), ('censys', True), ('xposedornot', True)])
def test_main_starts_exporter_without_import_side_effects(load_monitor, monkeypatch, tmp_path, name, configured):
    monitor, registry = load_monitor(name)
    namespace = monitor.main.__globals__
    server = Mock()
    monkeypatch.setitem(namespace, 'load_config', lambda: None)
    monkeypatch.setitem(namespace, 'start_http_server', server)
    monkeypatch.setitem(namespace, 'time', SimpleNamespace(time=lambda: 123, sleep=end_cycle, monotonic=lambda: 123))
    monkeypatch.setenv('CENSYS_TOKEN', 'test-key' if configured else '')
    monkeypatch.setenv('MY_PUBLIC_IP', '192.0.2.1' if configured else '')
    monkeypatch.delenv('HIBP_API_KEY', raising=False)
    monkeypatch.setenv('MY_EMAILS', 'person@example.com' if configured else '')
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    lookup = Mock(return_value=6)
    monkeypatch.setitem(namespace, 'scan' if name == 'censys' else 'check_email', lookup)
    with pytest.raises(EndCycle):
        monitor.main()
    server.assert_called_once_with(8000 if name == 'censys' else 8001)
    assert value(registry, f'{name}_monitor_enabled') == int(configured)
    assert lookup.call_count == int(configured)


@pytest.mark.parametrize('name', ['censys', 'xposedornot'])
def test_metrics_http_application_serializes_results(load_monitor, tmp_path, name):
    from prometheus_client import make_wsgi_app
    from prometheus_client.parser import text_string_to_metric_families
    monitor, registry = load_monitor(name)
    if name == 'censys':
        monitor.scan('test', '192.0.2.1', tmp_path,
            get=Mock(return_value=response(payload={'result': {'resource': {'services': [{'port': 443}]}}})))
    else:
        monitor.check_email('person@example.com', tmp_path, get=Mock(return_value=response(404, payload={'Error': 'Not found'})))
    status = []
    app = make_wsgi_app(registry)
    body = b''.join(app({'PATH_INFO': '/metrics', 'REQUEST_METHOD': 'GET',
                         'HTTP_ACCEPT': 'text/plain'}, lambda code, headers: status.append(code)))
    assert status == ['200 OK']
    metrics = {metric.name for metric in text_string_to_metric_families(body.decode())}
    assert f'{name}_scrape_success' in metrics
    assert b'test-key' not in body


def test_censys_valid_host_with_omitted_optional_services(load_monitor, tmp_path):
    monitor, registry = load_monitor('censys')
    host = {'ip': '192.0.2.1', 'location': {}}
    assert monitor.scan('secret', '192.0.2.1', tmp_path,
        get=Mock(return_value=response(payload={'result': {'resource': host}})))
    assert value(registry, 'censys_open_ports_total') == 0
    assert value(registry, 'censys_services_total') == 0
    assert value(registry, 'censys_scrape_success') == 1
    assert json.loads((tmp_path / 'censys_latest.json').read_text()) == host


@pytest.mark.parametrize('host', [{'ip': '192.0.2.2'}, {'ip': 'invalid'}, {'ip': None}])
def test_censys_missing_services_requires_matching_valid_host(load_monitor, tmp_path, host):
    monitor, registry = load_monitor('censys')
    assert not monitor.scan('secret', '192.0.2.1', tmp_path,
        get=Mock(return_value=response(payload={'result': {'resource': host}})))
    assert value(registry, 'censys_scrape_success') == 0
    assert math.isnan(value(registry, 'censys_open_ports_total'))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('emails', ['invalid-address', 'person @example.com', ','.join(f'p{i}@example.com' for i in range(101))])
def test_xposedornot_invalid_or_excessive_email_list_is_disabled(load_monitor, monkeypatch, tmp_path, emails):
    monitor, registry = load_monitor('xposedornot')
    namespace = monitor.main.__globals__
    monkeypatch.setitem(namespace, 'load_config', lambda: None)
    monkeypatch.setitem(namespace, 'start_http_server', Mock())
    monkeypatch.setitem(namespace, 'time', SimpleNamespace(sleep=end_cycle))
    monkeypatch.setenv('MY_EMAILS', emails)
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    lookup = Mock()
    monkeypatch.setitem(namespace, 'check_email', lookup)
    with pytest.raises(EndCycle):
        monitor.main()
    assert value(registry, 'xposedornot_monitor_enabled') == 0
    lookup.assert_not_called()
