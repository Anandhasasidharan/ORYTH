import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_scrape_targets_and_persistence():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    services = compose['services']
    config = yaml.safe_load((ROOT / 'prometheus/prometheus.yml').read_text())
    for scrape in config['scrape_configs']:
        target = scrape['static_configs'][0]['targets'][0]
        name, port = target.split(':')
        assert name in services
        assert f'localhost:{port}/metrics' in str(services[name]['healthcheck']['test'])
        assert services[name]['environment']['DATA_DIR'] == '/data'
        assert './data:/data' in services[name]['volumes']
    assert services['grafana']['ports'] == ['127.0.0.1:3000:3000']
    assert 'prometheus-data' in compose['volumes']


def test_dashboard_and_provisioning_use_same_datasource():
    provision = yaml.safe_load((ROOT / 'grafana/provisioning/datasources/datasource.yml').read_text())
    datasource = provision['datasources'][0]
    assert datasource['url'] == 'http://prometheus:9090'
    for path in (ROOT / 'grafana/dashboards').glob('*.json'):
        dashboard = json.loads(path.read_text())
        assert dashboard['uid']
        assert dashboard['panels']
        for panel in dashboard['panels']:
            assert panel['datasource']['uid'] == datasource['uid']
            for target in panel['targets']:
                assert 'vector(0)' not in target['expr']
                assert 'censys_risk_score' not in target['expr']


def test_all_yaml_files_parse():
    for path in ROOT.rglob('*.yml'):
        assert isinstance(yaml.safe_load(path.read_text()), dict), path
