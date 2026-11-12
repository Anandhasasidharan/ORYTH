"""Export free, keyless XposedOrNot email breach lookups."""
from collections import deque
from datetime import datetime, timezone
import hashlib
import logging
import math
import os
from pathlib import Path
import time
from urllib.parse import quote

import requests
from prometheus_client import Gauge, start_http_server

from monitor_common import configure_logging, load_config, write_json

breaches_gauge = Gauge('xposedornot_breaches_total', 'Known email breaches from XposedOrNot', ['email'])
enabled = Gauge('xposedornot_monitor_enabled', 'Valid email list configured')
success = Gauge('xposedornot_scrape_success', 'Last email lookup succeeded', ['email'])
last_success = Gauge('xposedornot_last_success_timestamp_seconds', 'Last successful email lookup', ['email'])


def parse_breaches(payload):
    """Accept documented name lists or the explicit no-match response."""
    if not isinstance(payload, dict):
        raise ValueError('Invalid breach response')
    if 'Error' in payload:
        if payload['Error'] == 'Not found' and not payload.get('breaches'):
            return []
        raise ValueError('Provider reported an error')
    if payload.get('status', 'success') != 'success':
        raise ValueError('Provider reported an unsuccessful lookup')
    groups = payload['breaches']
    if not isinstance(groups, list) or any(not isinstance(group, list) for group in groups):
        raise ValueError('Invalid breach list')
    names = [name for group in groups for name in group]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError('Invalid breach name')
    return list(dict.fromkeys(names))


def check_email(email, data_dir, get=requests.get):
    """Return wait time before the next request, honoring rate limits."""
    delay = 1.0
    status = None
    try:
        response = get(
            'https://api.xposedornot.com/v1/check-email/' + quote(email, safe=''),
            headers={'User-Agent': 'ORYTH-Dashboard', 'Accept': 'application/json'},
            timeout=20,
        )
        status = response.status_code
        if status == 429:
            delay = 3600.0
            try:
                retry_after = float(response.headers.get('Retry-After', delay))
                if math.isfinite(retry_after):
                    delay = max(1.0, retry_after)
            except (TypeError, ValueError):
                pass
        if status not in (200, 404):
            raise ValueError('XposedOrNot lookup failed')
        payload = response.json()
        if status == 404 and (not isinstance(payload, dict) or payload.get('Error') != 'Not found'):
            raise ValueError('Unexpected not-found response')
        breaches = parse_breaches(payload)
        identifier = hashlib.sha256(email.casefold().encode()).hexdigest()
        write_json(data_dir / f'xposedornot_{identifier}.json', {
            'provider': 'XposedOrNot', 'count': len(breaches), 'breaches': breaches,
            'checked_at': datetime.now(timezone.utc).isoformat(),
        })
        breaches_gauge.labels(email).set(len(breaches))
        last_success.labels(email).set(time.time())
        success.labels(email).set(1)
        logging.info('XposedOrNot email lookup succeeded')
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as error:
        logging.warning('XposedOrNot lookup failed (HTTP %s, %s); check quota and availability',
                        status if status is not None else 'unavailable', type(error).__name__)
        breaches_gauge.labels(email).set(math.nan)
        success.labels(email).set(0)
    return delay


def poll_emails(emails, data_dir, sleep=None, clock=None):
    """Space requests and limit each daily cycle to 25 attempts per rolling hour."""
    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    attempts = deque()
    for email in emails:
        while True:
            now = clock()
            while attempts and now - attempts[0] >= 3600:
                attempts.popleft()
            if len(attempts) < 25:
                break
            sleep(max(0.01, 3600 - (now - attempts[0])))
        attempts.append(clock())
        sleep(check_email(email, data_dir))


def main():
    load_config()
    configure_logging()
    emails = list(dict.fromkeys(e.strip().casefold() for e in os.getenv('MY_EMAILS', '').split(',') if e.strip()))
    if any('@' not in email or any(c.isspace() for c in email) for email in emails):
        logging.error('MY_EMAILS must contain comma-separated email addresses')
        emails = []
    if len(emails) > 100:
        logging.error('XposedOrNot free API supports at most 100 email checks per day; reduce MY_EMAILS')
        emails = []
    configured = bool(emails)
    enabled.set(int(configured))
    for email in emails:
        breaches_gauge.labels(email).set(math.nan)
        success.labels(email).set(0)
        last_success.labels(email).set(0)
    start_http_server(8001)
    if not configured:
        logging.warning('XposedOrNot disabled: configure MY_EMAILS (no API key required)')
    data_dir = Path(os.getenv('DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data')))
    while True:
        if configured:
            poll_emails(emails, data_dir)
        time.sleep(86400)


if __name__ == '__main__':
    main()
