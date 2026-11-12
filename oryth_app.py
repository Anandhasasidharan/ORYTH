"""Desktop entry point and packaged exporter worker entry point."""
import argparse
import json
from pathlib import Path
import runpy
import sys

from oryth.settings import resource_root


def run_exporter(name, synthetic=False):
    import os
    root = resource_root()
    sys.path.insert(0, str(root / 'scripts'))
    # Windowed PyInstaller apps have no Python stdout/stderr; give workers real streams.
    if os.getenv('ORYTH_SERVICE_LOG'):
        stream = open(os.environ['ORYTH_SERVICE_LOG'], 'a', encoding='utf-8', buffering=1)
        sys.stdout = stream
        sys.stderr = stream
    if synthetic:
        import requests
        payload = ({'result': {'resource': {'ip': '192.0.2.1', 'services': [{'port': 80}, {'port': 443}]}}}
                   if name == 'censys' else {'breaches': [['SyntheticOne', 'SyntheticTwo']], 'status': 'success'})
        def synthetic_get(*args, **kwargs):
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps(payload).encode()
            return response
        requests.get = synthetic_get
    runpy.run_path(str(root / 'scripts' / f'{name}-monitor.py'), run_name='__main__')


def main():
    parser = argparse.ArgumentParser(description='ORYTH desktop application')
    parser.add_argument('--exporter', choices=['censys', 'xposedornot'], help=argparse.SUPPRESS)
    parser.add_argument('--synthetic', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--self-test', action='store_true', help='Run an isolated synthetic end-to-end test')
    parser.add_argument('--check-gui', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.exporter:
        run_exporter(args.exporter, args.synthetic)
        return 0
    if args.self_test:
        from oryth.selftest import run
        return run(args.report, args.runtime)
    if args.check_gui:
        import tempfile
        import tkinter as tk
        from oryth.desktop import DesktopApp
        with tempfile.TemporaryDirectory(prefix='oryth-gui-test-') as directory:
            root = tk.Tk()
            root.withdraw()
            app = DesktopApp(root, directory)
            root.update_idletasks()
            assert app.start_button['text'] == 'Start monitoring'
            root.after(100, root.destroy)
            root.mainloop()
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps({'gui': 'PASS'}), encoding='utf-8')
        return 0
    from oryth.desktop import run
    run()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Make failures in --windowed self-tests visible to the Windows build job.
        import traceback
        if '--report' in sys.argv:
            target = Path(sys.argv[sys.argv.index('--report') + 1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({'error': str(error), 'traceback': traceback.format_exc()}, indent=2), encoding='utf-8')
        raise
