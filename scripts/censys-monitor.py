from dotenv import load_dotenv
load_dotenv()   # ← THIS LINE WAS BROKEN BEFORE (load_dotimport → load_dotenv)

import os
import json
import time
import requests
from prometheus_client import start_http_server, Gauge
from pathlib import Path

Path("./data").mkdir(exist_ok=True)

CENSYS_TOKEN = os.getenv('CENSYS_TOKEN')
MY_IP = os.getenv('MY_PUBLIC_IP', '').strip()

if not CENSYS_TOKEN or not MY_IP:
    print("FATAL: Missing CENSYS_TOKEN or MY_PUBLIC_IP")
    exit(1)

open_ports = Gauge('censys_open_ports_total', 'Open ports')
services   = Gauge('censys_services_total', 'Services')
certs      = Gauge('censys_certificates_total', 'Certificates')
risk       = Gauge('censys_risk_score', 'Risk score')

def scan():
    print(f"[CENSYS] Scanning {MY_IP} at {time.strftime('%X')}")
    try:
        r = requests.get(
            f"https://api.platform.censys.io/v3/global/asset/host/{MY_IP}",
            headers={"Authorization": f"Bearer {CENSYS_TOKEN}"},
            timeout=20
        )
        if r.status_code == 200:
            host = r.json().get('result', {}).get('host', {})
            svcs = host.get('services', [])
            ports = len({s.get('port') for s in svcs if s.get('port')})

            open_ports.set(ports)
            services.set(len(svcs))
            certs.set(len(host.get('certificates', [])))
            risk.set(host.get('risk', {}).get('score', 0))

            with open("./data/censys_latest.json", "w") as f:
                json.dump(host, f, indent=2)

            print(f"CENSYS SUCCESS → {ports} open ports | Risk {host.get('risk',{}).get('score',0)}")
        elif r.status_code == 404:
            print("CENSYS: IP not indexed yet")
            open_ports.set(0); services.set(0); certs.set(0); risk.set(0)
        else:
            print(f"CENSYS {r.status_code}: {r.text}")
    except Exception as e:
        print(f"CENSYS ERROR: {e}")

# THIS WILL KEEP THE CONTAINER ALIVE FOREVER
start_http_server(8000)
print("CENSYS EXPORTER IS ALIVE ON PORT 8000")
scan()
while True:
    time.sleep(3600)
    scan()