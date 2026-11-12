"""Export Censys host observations to Prometheus."""
import ipaddress
import logging
import math
import os
from pathlib import Path
import time

import requests
from prometheus_client import Gauge, start_http_server

from monitor_common import configure_logging, load_config, write_json

open_ports = Gauge('censys_open_ports_total', 'Distinct observed port numbers')
services = Gauge('censys_services_total', 'Observed services')
enabled = Gauge('censys_monitor_enabled', 'Censys credentials and IP configured')
success = Gauge('censys_scrape_success', 'Last Censys lookup succeeded')
last_success = Gauge('censys_last_success_timestamp_seconds', 'Last successful lookup')


def scan(token, ip, data_dir, organization_id='', get=requests.get):
    """Return success; leave failed or unknown observations as NaN."""
    status = None
    try:
        params = {'organization_id': organization_id} if organization_id else {}
        response = get(
            f'https://api.platform.censys.io/v3/global/asset/host/{ip}',
            headers={'Authorization': f'Bearer {token}',
                     'Accept': 'application/vnd.censys.api.v3.host.v1+json'},
            params=params, timeout=20,
        )
        status = response.status_code
        if response.status_code != 200:
            raise ValueError(f'Censys HTTP {response.status_code}')
        host = response.json()['result']['resource']
        if not isinstance(host, dict):
            raise ValueError('Invalid host response')
        if 'services' in host:
            observations = host['services']
        else:
            # Censys omits empty optional fields on some valid host records.
            # Validate the returned host identity before treating an omitted list as empty.
            if ipaddress.ip_address(host.get('ip', '')) != ipaddress.ip_address(ip):
                raise ValueError('Unexpected host identity')
            observations = []
        if not isinstance(observations, list):
            raise ValueError('Invalid services response')
        ports = {s['port'] for s in observations}
        if any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
            raise ValueError('Invalid service port')
        write_json(data_dir / 'censys_latest.json', host)
        open_ports.set(len(ports))
        services.set(len(observations))
        last_success.set(time.time())
        success.set(1)
        logging.info('Censys lookup succeeded: %d ports, %d services', len(ports), len(observations))
        return True
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as error:
        logging.warning('Censys lookup failed (HTTP %s, %s); check configuration, quota and availability',
                        status if status is not None else 'unavailable', type(error).__name__)
        open_ports.set(math.nan)
        services.set(math.nan)
        success.set(0)
        return False


def main():
    load_config()
    configure_logging()
    token = os.getenv('CENSYS_TOKEN', '').strip()
    ip = os.getenv('MY_PUBLIC_IP', '').strip()
    configured = bool(token and ip)
    if configured:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logging.error('MY_PUBLIC_IP must be an IPv4 or IPv6 address')
            configured = False
    enabled.set(int(configured))
    open_ports.set(math.nan)
    services.set(math.nan)
    start_http_server(8000)
    if not configured:
        logging.warning('Censys disabled: configure CENSYS_TOKEN and MY_PUBLIC_IP')
    data_dir = Path(os.getenv('DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data')))
    while True:
        if configured:
            scan(token, ip, data_dir, os.getenv('CENSYS_ORGANIZATION_ID', '').strip())
        time.sleep(3600)


if __name__ == '__main__':
    main()
