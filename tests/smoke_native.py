"""Reproduce the desktop app's synthetic end-to-end test from source."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
report = Path(tempfile.mkdtemp(prefix='oryth-native-test-')) / 'report.json'
command = [sys.executable, str(root / 'oryth_app.py'), '--self-test', '--report', str(report)]
existing = Path('/tmp/oryth-native-runtime')
if existing.exists():
    command += ['--runtime', str(existing)]
result = subprocess.run(command)
print(report.read_text(encoding='utf-8') if report.exists() else 'No report was produced.')
print('Report:', report)
sys.exit(result.returncode)
