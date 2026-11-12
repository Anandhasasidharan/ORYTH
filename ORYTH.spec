# Build on Windows: python -m PyInstaller --clean --noconfirm ORYTH.spec
from pathlib import Path

root = Path(SPECPATH)
datas = [(str(root / 'scripts' / name), 'scripts') for name in
         ('censys-monitor.py', 'xposedornot-monitor.py', 'monitor_common.py')]
datas += [(str(root / 'grafana'), 'grafana'), (str(root / 'prometheus'), 'prometheus')]
a = Analysis([str(root / 'oryth_app.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=['requests', 'prometheus_client', 'dotenv', 'ipaddress'],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='ORYTH', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          version=str(root / 'packaging' / 'version_info.txt'),
          manifest=str(root / 'packaging' / 'windows.manifest'))
