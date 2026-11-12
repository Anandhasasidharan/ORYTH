import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_scrape_targets_are_local_services():
    config = yaml.safe_load((ROOT / 'prometheus/prometheus.yml').read_text())
    targets = {scrape['job_name']: scrape['static_configs'][0]['targets'][0]
               for scrape in config['scrape_configs']}
    assert targets == {'censys': '127.0.0.1:8000', 'xposedornot': '127.0.0.1:8001'}


def test_dashboard_and_provisioning_use_same_datasource():
    provision = yaml.safe_load((ROOT / 'grafana/provisioning/datasources/datasource.yml').read_text())
    datasource = provision['datasources'][0]
    assert datasource['url'] == 'http://127.0.0.1:9090'
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
    for folder in (ROOT / 'prometheus', ROOT / 'grafana', ROOT / '.github'):
        for path in folder.rglob('*.yml'):
            assert isinstance(yaml.safe_load(path.read_text()), dict), path
