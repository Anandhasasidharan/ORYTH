# ORYTH — Personal Cyber Risk Dashboard

A Windows desktop app for monitoring email breach exposure and optional public-IP exposure. It runs locally, manages its own dashboard, and uses the free XposedOrNot email API. No Python, WSL, containers, or paid breach API key is required for the Windows download.

## Windows quick start

1. Download **ORYTH-Windows-x64.zip** from [Releases](https://github.com/Anandhasasidharan/ORYTH/releases).
2. Extract the ZIP and double-click **ORYTH.exe**.
3. Enter the email addresses you want to monitor.
4. Optional: enter your public IP and Censys Platform token to enable network exposure monitoring.
5. Click **Start monitoring**. The first start downloads and verifies Grafana and Prometheus automatically. Later starts reuse the cached components.
6. Click **Copy password**, then **Open dashboard**. Sign in as **admin** using the copied password.

Keep the desktop window open while monitoring. **Stop** or closing the window stops all four local processes. Windows 10/11 **x64**, internet access, and free space for the downloaded components are required. No administrator installation or Windows service setup is needed. The application is currently an unsigned desktop preview; release checks cover executable startup and the native stack, rather than a formal Windows compatibility certification.

## What it monitors

- **Email breaches:** XposedOrNot is checked daily. Results show known breach counts for each address and the total across monitored addresses. A breach affecting two addresses counts twice in that total. No breach API key is needed.
- **Network exposure (optional):** Censys is checked hourly for observations of open ports and services on your configured public IP. A [Censys Platform Personal Access Token](https://docs.censys.com/reference/get-started) is required. These are Censys observations, rather than a live port scan.
- **Monitoring health:** the dashboard displays integration status and time since the last successful lookup. Missing or failed lookups remain unknown; they are never silently reported as clean results.

The free XposedOrNot endpoint supports 25 checks/hour and 100/day per public IP. ORYTH spaces requests, enforces the hourly budget within a daily cycle, accepts at most 100 unique addresses, and honors rate-limit backoff. Other users of your public IP and repeated app restarts share the provider's quota. Breach coverage may differ from other providers. The basic endpoint returns breach names rather than dates, so ORYTH does not invent a days-since-breach result.

## Where your data goes

When monitoring starts, configured email addresses are sent over HTTPS to `api.xposedornot.com`. If network monitoring is enabled, the configured public IP and token are sent to `api.platform.censys.io`. No API requests are made by the desktop window until you start monitoring.

Settings, the Censys token, generated dashboard password, downloaded components, logs, snapshots, and metrics are stored under:

```text
%LOCALAPPDATA%\ORYTH
```

Use **Open data folder** to find them. Settings are local to your Windows account, not bundled into the executable or committed to this repository. The dashboard password is generated on first use and saved with the settings. Initial credentials do not reset an existing Grafana database.

Grafana, Prometheus and both exporters listen only on the local computer: ports **3000**, **9090**, **8000**, and **8001**. Another app using one of those ports must be stopped before ORYTH starts. Metrics are retained for 30 days. Failed lookups preserve the last successful JSON snapshot while marking current metrics as unknown. Old snapshots are not loaded as current results at startup.

## Build the Windows application

Use Windows with Python **3.12 x64**, including Tcl/Tk. From the repository root, in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ORYTH.spec
```

`dist\ORYTH.exe` is a portable executable containing the Python app and its Python/Tk dependencies. It downloads the independent dashboard components on first start; they are not part of the executable. Only selected scripts and public configuration are bundled. `.env`, user settings, personal snapshots, development caches, and logs are excluded.

To create the distributable ZIP and checksum file, activate the virtual environment and run:

```powershell
.\.venv\Scripts\Activate.ps1
.\packaging\build-windows.ps1
```

The output is `dist\ORYTH-Windows-x64.zip` and `dist\SHA256SUMS.txt`. The [Windows application workflow](https://github.com/Anandhasasidharan/ORYTH/actions/workflows/windows.yml) runs the tests, builds the executable on Windows, checks the packaged desktop window, and tests the packaged app against real Windows Grafana and Prometheus processes with synthetic API data. Successful builds upload the ZIP and its checksum as workflow artifacts.

## Run from source

On Windows, install `requirements.txt` and launch:

```powershell
python oryth_app.py
```

The same desktop code also supports Linux x64 with Tcl/Tk installed. An optional console launcher is available for WSL/Linux or development:

```bash
python3 scripts/run-local.py
```

Console mode can read a local `.env` copied from `config/.env.example`, or use saved application settings. The desktop app uses its setup form and per-user settings instead of requiring `.env`. Older `HIBP_API_KEY` entries are ignored. Runtime binaries are downloaded automatically, or can be supplied through the console launcher's `--runtime` argument. Existing development binaries under `/tmp/oryth-native-runtime` can be reused with that argument.

## Tests and troubleshooting

Install `requirements-dev.txt`, then run the unit tests:

```bash
python3 -m pytest -q
```

To run the synthetic native stack test from source:

```bash
python3 tests/smoke_native.py
```

The test starts real local services, verifies expected metrics, checks dashboard provisioning and all dashboard queries, then stops the services. External API calls are replaced with synthetic responses; your email addresses and credentials are not sent to either provider. It prints the validation report path.

For a packaged executable, `--self-test --report <path>` runs the same test; `--check-gui --report <path>` checks that its desktop window can be created. These commands are intended for release validation.

If startup fails, open the data folder and inspect `logs`. A port-conflict message means another instance or application is running. Failed downloads can be retried with **Start monitoring**; archives must match upstream SHA256 checksums before they are installed. Dashboard availability confirms the local services are running; check the lookup-status panels separately for API success. Authentication or quota errors remain visible as failed lookups.

## References

- [XposedOrNot free API and limits](https://xposedornot.com/api_doc)
- [Censys host lookup and authentication](https://docs.censys.com/reference/get-started)
- [Grafana Windows installation](https://grafana.com/docs/grafana/latest/setup-grafana/installation/windows/)
- [Prometheus downloads](https://prometheus.io/download/)
- [Third-party components](THIRD_PARTY.md)
