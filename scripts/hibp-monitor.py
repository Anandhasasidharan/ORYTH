from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import requests
from prometheus_client import start_http_server, Gauge
from pathlib import Path

# --- Make sure data folder exists (Windows + Docker safe) ---
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

EMAILS = [e.strip() for e in os.getenv('MY_EMAILS', '').split(',') if e.strip()]

breaches_gauge = Gauge('hibp_breaches_total', 'Number of breaches (Firefox Monitor)', ['email'])
last_breach_gauge = Gauge('hibp_last_breach_days_ago', 'Days since last breach', ['email'])

def check_email(email):
    url = f"https://monitor.firefox.com/api/v1/breachedaccount/{email}"
    try:
        r = requests.get(url, headers={"User-Agent": "ORYTH-Dashboard"}, timeout=10)
        if r.status_code == 200:
            breaches = r.json()
            count = len(breaches)
            latest = max(b['AddedDate'] for b in breaches) if breaches else None
            days_ago = int((time.time() - time.mktime(time.strptime(latest[:19], "%Y-%m-%dT%H:%M:%S"))) / 86400) if latest else -1
        else:
            count = 0
            days_ago = -1

        breaches_gauge.labels(email).set(count)
        last_breach_gauge.labels(email).set(days_ago if days_ago > 0 else 999)
        print(f"{email}: {count} breaches")

        # Save using cross-platform path
        safe_name = email.split("@")[0]
        with open(DATA_DIR / f"hibp_{safe_name}.json", 'w', encoding='utf-8') as f:
            json.dump({"count": count, "breaches": breaches if 'breaches' in locals() else []}, f, indent=2)

    except Exception as e:
        print(f"Error checking {email}: {e}")

start_http_server(8001)
print("HIBP (Firefox Monitor) monitor started on port 8001")

while True:
    for email in EMAILS:
        if email:
            check_email(email)
    time.sleep(86400)  # once per day