"""Export existing Shodan host observations; never submit an active scan."""
import ipaddress
import logging
import math
import os
from pathlib import Path
import time
from urllib.parse import quote

import requests
from prometheus_client import start_http_server

from monitor_common import configure_logging, load_config, write_json
from network_metrics import NetworkMetrics

metrics = NetworkMetrics('shodan', 'Shodan')
open_ports = metrics.open_ports
services = metrics.services
enabled = metrics.enabled
success = metrics.success
last_success = metrics.last_success


def parse_host(payload, ip):
    if not isinstance(payload, dict) or ipaddress.ip_address(payload.get('ip_str', '')) != ipaddress.ip_address(ip):
        raise ValueError('Invalid or mismatched host identity')
    ports = payload['ports']
    observations = payload['data']
    if not isinstance(ports, list) or not isinstance(observations, list):
        raise ValueError('Invalid host observations')
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        raise ValueError('Invalid port number')
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError('Invalid service observation')
        port = observation.get('port')
        if type(port) is not int or not 1 <= port <= 65535 or port not in ports:
            raise ValueError('Invalid service port')
    return len(set(ports)), len(observations)


def scan(api_key, ip, data_dir, get=requests.get):
    status = None
    try:
        ip = str(ipaddress.ip_address(ip))
        response = get('https://api.shodan.io/shodan/host/' + quote(ip, safe=':'),
                       params={'key': api_key, 'history': 'false', 'minify': 'false'},
                       headers={'User-Agent': 'ORYTH-Dashboard', 'Accept': 'application/json'}, timeout=20)
        status = response.status_code
        if status != 200:
            raise ValueError('Shodan host lookup failed')
        host = response.json()
        port_count, service_count = parse_host(host, ip)
        write_json(data_dir / 'shodan_latest.json', host)
        open_ports.set(port_count)
        services.set(service_count)
        last_success.set(time.time())
        success.set(1)
        logging.info('Shodan lookup succeeded: %d ports, %d services', port_count, service_count)
        return True
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as error:
        # Shodan puts the API key in query parameters. Never log URLs, exception text or bodies.
        logging.warning('Shodan lookup failed (HTTP %s, %s); check API access, IP, quota and availability',
                        status if status is not None else 'unavailable', type(error).__name__)
        open_ports.set(math.nan)
        services.set(math.nan)
        success.set(0)
        return False


def main():
    load_config()
    configure_logging()
    key = os.getenv('SHODAN_API_KEY', '').strip()
    ip = os.getenv('MY_PUBLIC_IP', '').strip()
    configured = bool(key and ip)
    if configured:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logging.error('MY_PUBLIC_IP must be an IPv4 or IPv6 address')
            configured = False
    enabled.set(int(configured))
    open_ports.set(math.nan)
    services.set(math.nan)
    start_http_server(8000, addr='127.0.0.1')
    if not configured:
        logging.warning('Shodan disabled: configure SHODAN_API_KEY and MY_PUBLIC_IP')
    data_dir = Path(os.getenv('DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data')))
    while True:
        if configured:
            scan(key, ip, data_dir)
        time.sleep(3600)


if __name__ == '__main__':
    main()
