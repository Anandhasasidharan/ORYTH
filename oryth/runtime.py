"""Download verified upstream runtimes into the user's application directory."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile

import requests

VERSIONS = {'prometheus': '3.5.0', 'grafana': '12.3.0'}


class SetupCancelled(RuntimeError):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise SetupCancelled('Setup cancelled.')


def artifact(name, system=None):
    system = system or ('windows' if os.name == 'nt' else 'linux')
    if system not in ('windows', 'linux'):
        raise RuntimeError('This release supports Windows and Linux on x64 processors.')
    version = VERSIONS[name]
    extension = 'zip' if system == 'windows' else 'tar.gz'
    filename = f'{name}-{version}.{system}-amd64.{extension}'
    if name == 'prometheus':
        base = f'https://github.com/prometheus/prometheus/releases/download/v{version}/'
        return filename, base + filename, base + 'sha256sums.txt'
    base = 'https://dl.grafana.com/oss/release/'
    return filename, base + filename, base + filename + '.sha256'


def verify_archive(path, checksum_text, filename):
    lines = checksum_text.strip().splitlines()
    expected = None
    for line in lines:
        fields = line.split()
        if len(fields) == 1 and len(lines) == 1:
            expected = fields[0]
        elif len(fields) >= 2 and fields[-1].lstrip('*') == filename:
            expected = fields[0]
    if not expected or not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
        raise ValueError('Publisher checksum is missing or invalid.')
    with Path(path).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest.lower() != expected.lower():
        raise ValueError('Download checksum failed. Please retry setup.')
    return digest


def extract_archive(path, destination):
    destination = Path(destination)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                normalized = entry.filename.replace('\\', '/')
                parts = PurePosixPath(normalized).parts
                if (normalized.startswith('/') or '..' in parts or ':' in normalized
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise ValueError('Unsafe path in downloaded archive.')
            archive.extractall(destination)
    else:
        with tarfile.open(path) as archive:
            archive.extractall(destination, filter='data')


def find_binary(directory, name, system=None):
    system = system or ('windows' if os.name == 'nt' else 'linux')
    suffix = '.exe' if system == 'windows' else ''
    choices = [name + suffix]
    if name == 'grafana':
        choices.append('grafana-server' + suffix)
    for choice in choices:
        for path in Path(directory).rglob(choice):
            if path.is_file():
                return path
    return None


def ensure_runtime(directory, progress=lambda message: None, cancel=None):
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Download the x64 release on a Windows or Linux x64 machine.')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    result = {}
    for name in ('prometheus', 'grafana'):
        check_cancel(cancel)
        folder = directory / name
        binary = find_binary(folder, name)
        marker = folder / '.oryth-runtime.json'
        if binary and marker.exists():
            metadata = json.loads(marker.read_text())
            if metadata.get('version') == VERSIONS[name]:
                result[name] = binary
                continue
        # Reuse a native runtime explicitly supplied by a source developer.
        if binary and not marker.exists():
            result[name] = binary
            continue
        filename, url, checksum_url = artifact(name)
        progress(f'Downloading {name.title()}…')
        with tempfile.TemporaryDirectory(prefix=f'.{name}-', dir=directory) as temporary:
            temporary = Path(temporary)
            archive = temporary / filename
            with requests.get(url, stream=True, timeout=(15, 60)) as response:
                response.raise_for_status()
                total = int(response.headers.get('Content-Length', 0))
                received = 0
                last_percent = -1
                with archive.open('wb') as stream:
                    for chunk in response.iter_content(1024 * 1024):
                        check_cancel(cancel)
                        if not chunk:
                            continue
                        stream.write(chunk)
                        received += len(chunk)
                        percent = min(100, int(received * 100 / total)) if total else -1
                        if percent != last_percent and percent >= 0:
                            progress(f'Downloading {name.title()}… {percent}%')
                            last_percent = percent
            check_cancel(cancel)
            progress(f'Checking {name.title()} download…')
            response = requests.get(checksum_url, timeout=30)
            response.raise_for_status()
            digest = verify_archive(archive, response.text, filename)
            unpacked = temporary / 'unpacked'
            unpacked.mkdir()
            extract_archive(archive, unpacked)
            check_cancel(cancel)
            if not find_binary(unpacked, name):
                raise ValueError(f'The {name} download is missing its executable.')
            (unpacked / '.oryth-runtime.json').write_text(json.dumps({
                'version': VERSIONS[name], 'sha256': digest,
            }))
            if folder.exists():
                shutil.rmtree(folder)
            os.replace(unpacked, folder)
        result[name] = find_binary(folder, name)
    return result
