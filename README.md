# ORYTH — Personal Cyber Risk Dashboard

Self-hosted monitoring of your public IP and email breach exposure, using Python exporters, Prometheus, and Grafana.

Censys supplies existing observations of open ports and services; ORYTH looks them up hourly. These are observations from Censys, not an active or real-time scan. The free, keyless XposedOrNot API supplies email breach results, checked daily. Prometheus scrapes both exporters every 15 seconds and retains metrics for 30 days.

## Configure monitoring

If `.env` does not exist yet:

```bash
cp config/.env.example .env
```

Edit `.env` with your settings:

- `CENSYS_TOKEN`: a [Censys Platform Personal Access Token](https://docs.censys.com/reference/get-started).
- `MY_PUBLIC_IP`: the IPv4 or IPv6 address to look up.
- `CENSYS_ORGANIZATION_ID`: optional, to use organization entitlements.
- `MY_EMAILS`: comma-separated email addresses to monitor through [XposedOrNot](https://xposedornot.com/api_doc). No breach API key or paid subscription is required. Old `HIBP_API_KEY` entries are ignored.
- `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`: credentials for the initial Grafana admin account. Defaults are `admin` / `admin` when absent; set your password before starting.

Unused integration values can remain blank. The corresponding exporter stays available and reports disabled; unknown results do not become zero breaches or zero open ports.

## Run directly in WSL/Linux (no Docker)

The app can run as four native processes. Install the Python dependencies from `requirements.txt` in a virtual environment, and obtain the Linux binaries from the official [Prometheus downloads](https://prometheus.io/download/) and [Grafana downloads](https://grafana.com/grafana/download) pages. Verify their published SHA256 checksums.

The launcher searches `PATH`, then `/tmp/oryth-native-runtime/prometheus/*/prometheus` and `/tmp/oryth-native-runtime/grafana/*/bin/grafana`. Set `GRAFANA_HOME` if your Grafana installation stores its `conf/` and `public/` directories separately from the executable.

From the directory containing this README:

```bash
python3 scripts/run-local.py
```

Open [Grafana](http://127.0.0.1:3000/d/oryth-cyber-risk). The launcher reads your existing `.env`, generates configuration using localhost addresses, and saves logs, snapshots and databases under `/tmp/oryth-local-state`. Set `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` in `.env` before the first launch; the fallback credentials are `admin` / `admin`. Initial credentials do not reset an existing Grafana database.

Press Ctrl+C to stop all four processes. The launcher also stops the stack if any process exits. For storage that survives temporary-file cleanup, specify a persistent state directory:

```bash
python3 scripts/run-local.py --state "$PWD/.oryth-state"
```

To repeat the full native smoke test with synthetic data, while the normal stack is stopped:

```bash
python3 tests/smoke_native.py
```

This starts real exporters, Prometheus and Grafana on local ports, checks all dashboard queries and expected metric values, then stops the services. It uses dummy credentials, synthetic addresses and mocked external API responses. It never sends your configured credentials to Censys or XposedOrNot. The report path is printed when the test finishes. Synthetic tests do not establish breach coverage for your own addresses. The XposedOrNot endpoint was also tested separately using its public documentation sample address.

## Run with Docker (optional)

Install Docker Engine with the Compose plugin, or Docker Desktop with Linux containers enabled. Run these commands from the directory containing this README and `docker-compose.yml` (the repository root).

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open [Grafana](http://localhost:3000/d/oryth-cyber-risk) and sign in with your configured credentials. Allow about 30 seconds for the first Prometheus scrape. Grafana is bound to localhost; Prometheus and the exporters are accessible only inside the Compose network.

The dashboard shows port and service counts, total and per-email breach counts, integration status, and time since the last successful lookup. Missing credentials, unindexed hosts, API failures, and unavailable exporters display disabled/failed or unknown values. Total breach count is unknown if any configured email lookup fails. A breach affecting two monitored addresses counts once for each address. Breach counts reflect XposedOrNot's database and can differ from other providers. The basic endpoint returns breach names, so no breach-date or days-since-breach metric is invented.

## Check and troubleshoot

For the optional Docker setup, after allowing about 30 seconds for scraping, validate Grafana health, both Prometheus targets, and every dashboard query:

```bash
python3 scripts/check-stack.py
```

This checks infrastructure and query syntax. Check dashboard lookup status separately to confirm live API access.

```bash
docker compose logs --tail=100 censys xposedornot prometheus grafana
```

Exporter container health checks confirm the metrics endpoint is running; check dashboard lookup status for API success. HTTP 401/403 usually requires checking credentials and permissions. A Censys 404 is treated as unknown, not a clean scan. Only XposedOrNot's explicit `{"Error":"Not found"}` response is accepted as zero breaches; unexpected 404s and malformed responses remain unknown. Requests are spaced at least one second apart, batches respect 25 attempts per rolling hour, and configuration is limited to 100 unique addresses per daily cycle. HTTP 429 honors a numeric `Retry-After` header, with a one-hour fallback. These budgets are local to one running exporter; repeated restarts and other users of your public IP share the provider's quota. Failed addresses are checked again during the next daily cycle.

Snapshots are stored in `data/` using atomic writes. Failed lookups preserve the last successful snapshot while setting the current result metrics to unknown and lookup status to failed. Existing snapshots are historical and are not loaded as current results at startup. XposedOrNot filenames hash the full email address, preventing collisions between addresses with the same local part. Metrics still contain email labels, so keep access to this dashboard private.

Grafana and Prometheus retain their state in named Docker volumes. On an existing Grafana volume, changing the initial admin credentials in `.env` does not reset the existing account password. To stop services while retaining data:

```bash
docker compose down
```

Rebuild after changing Python code. Restart/recreate exporters after changing credentials:

```bash
docker compose up --build -d
```

## Local development and tests

Python 3.12 or later:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use synthetic API responses and temporary data. They cover successful responses, failures, rate limiting, malformed payloads, exporter startup, metrics serialization, persistence, and configuration consistency. They do not contact real accounts.

Optional local diagnostics (use `python3` outside the activated virtual environment):

```bash
python debug_env.py
python apicheck.py
```

`debug_env.py` reports only configuration presence. `apicheck.py` performs one real Censys lookup, saves a successful result, and exits with status 0 on success, 1 on lookup failure, or 2 on invalid configuration. This may consume Censys credits.

To run an exporter without Docker:

```bash
python scripts/censys-monitor.py
python scripts/xposedornot-monitor.py
```

Run each exporter in its own terminal. Local runs read `.env` relative to the project directory and save to the project's `data/` directory, regardless of the shell's working directory. Set `DATA_DIR` to override the output directory.

## API references

- [Censys host lookup and response schema](https://docs.censys.com/reference/get-started)
- [XposedOrNot free API, response models and rate limits](https://xposedornot.com/api_doc)
