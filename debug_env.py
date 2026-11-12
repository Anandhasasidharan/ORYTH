"""Report configuration presence without exposing secret values."""
import os
from pathlib import Path
from dotenv import load_dotenv


def main():
    load_dotenv(Path(__file__).resolve().parent / '.env')
    for name in ('CENSYS_TOKEN', 'MY_PUBLIC_IP', 'CENSYS_ORGANIZATION_ID',
                 'MY_EMAILS', 'GRAFANA_ADMIN_PASSWORD'):
        print(f'{name}: {"configured" if os.getenv(name, "").strip() else "missing"}')


if __name__ == '__main__':
    main()
