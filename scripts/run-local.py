"""Optional source-mode console launcher; desktop users run ORYTH.exe."""
import argparse
import os
from pathlib import Path
import signal
import sys
import time

from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oryth.services import ServiceManager
from oryth.settings import load_settings, user_directory, validate_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--state', type=Path, default=user_directory())
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    settings = load_settings(args.state)
    settings.update(censys_token=os.getenv('CENSYS_TOKEN', settings['censys_token']),
                    public_ip=os.getenv('MY_PUBLIC_IP', settings['public_ip']),
                    organization_id=os.getenv('CENSYS_ORGANIZATION_ID', settings['organization_id']),
                    emails=os.getenv('MY_EMAILS', ','.join(settings['emails'])),
                    dashboard_password=os.getenv('GRAFANA_ADMIN_PASSWORD', settings['dashboard_password']))
    settings = validate_settings(settings)
    from oryth.settings import save_settings
    save_settings(args.state, settings)
    manager = ServiceManager(args.state, args.runtime)
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        manager.start(settings, progress=print)
        print('ORYTH: http://127.0.0.1:3000/d/oryth-cyber-risk', flush=True)
        print('Press Ctrl+C to stop. Dashboard username: admin; password is in your saved settings.', flush=True)
        while True:
            manager.check_processes()
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        manager.stop()


if __name__ == '__main__':
    sys.exit(main())
