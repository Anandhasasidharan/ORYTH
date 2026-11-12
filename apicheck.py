"""Perform one configured Censys lookup and return a useful exit status."""
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
    token = os.getenv('CENSYS_TOKEN', '').strip()
    ip = os.getenv('MY_PUBLIC_IP', '').strip()
    if not token or not ip:
        print('Configure CENSYS_TOKEN and MY_PUBLIC_IP in .env first.')
        return 2
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        print('MY_PUBLIC_IP must be an IPv4 or IPv6 address.')
        return 2
    monitor = runpy.run_path(str(root / 'scripts' / 'censys-monitor.py'))
    ok = monitor['scan'](token, ip, Path(os.getenv('DATA_DIR', str(root / 'data'))),
                         os.getenv('CENSYS_ORGANIZATION_ID', '').strip())
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
