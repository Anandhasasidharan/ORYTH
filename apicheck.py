"""Perform one configured Shodan or Censys host lookup."""
import ipaddress
import os
from pathlib import Path
import runpy
import sys


def main():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / 'scripts'))
    from monitor_common import configure_logging, load_config
    load_config()
    configure_logging()
    provider = os.getenv('NETWORK_PROVIDER') or ('shodan' if os.getenv('SHODAN_API_KEY') else 'censys')
    if provider not in ('shodan', 'censys'):
        print('NETWORK_PROVIDER must be shodan or censys.')
        return 2
    credential_name = 'SHODAN_API_KEY' if provider == 'shodan' else 'CENSYS_TOKEN'
    key = os.getenv(credential_name, '').strip()
    ip = os.getenv('MY_PUBLIC_IP', '').strip()
    if not key or not ip:
        print(f'Configure {credential_name} and MY_PUBLIC_IP in .env first.')
        return 2
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        print('MY_PUBLIC_IP must be an IPv4 or IPv6 address.')
        return 2
    monitor = runpy.run_path(str(root / 'scripts' / f'{provider}-monitor.py'))
    options = {'organization_id': os.getenv('CENSYS_ORGANIZATION_ID', '').strip()} if provider == 'censys' else {}
    ok = monitor['scan'](key, ip, Path(os.getenv('DATA_DIR', str(root / 'data'))), **options)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
