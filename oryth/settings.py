"""Per-user application settings and resource paths."""
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import sys


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))


def user_directory():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'ORYTH'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'oryth'


def validate_settings(values):
    token = str(values.get('censys_token', '')).strip()
    ip = str(values.get('public_ip', '')).strip()
    if bool(token) != bool(ip):
        raise ValueError('Enter both the public IP and Censys token, or leave both blank.')
    if ip:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError('Enter a valid public IPv4 or IPv6 address.') from None
    raw = values.get('emails', [])
    if isinstance(raw, str):
        raw = re.split(r'[,;\n]+', raw)
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ValueError('Enter email addresses separated by commas or new lines.')
    emails = list(dict.fromkeys(item.strip().casefold() for item in raw if item.strip()))
    if len(emails) > 100:
        raise ValueError('The free service supports up to 100 email checks per day.')
    if any(not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) for email in emails):
        raise ValueError('Check the email addresses; each must look like name@example.com.')
    password = values.get('dashboard_password') or secrets.token_urlsafe(24)
    return {'censys_token': token, 'public_ip': ip, 'emails': emails,
            'organization_id': str(values.get('organization_id', '')).strip(),
            'dashboard_password': password}


def save_settings(directory, values):
    values = validate_settings(values)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'settings.json'
    temporary = directory / 'settings.json.tmp'
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(values, stream, indent=2)
    temporary.chmod(0o600)
    os.replace(temporary, path)
    return values


def load_settings(directory):
    path = Path(directory) / 'settings.json'
    if path.exists():
        return validate_settings(json.loads(path.read_text(encoding='utf-8')))
    return validate_settings({})
