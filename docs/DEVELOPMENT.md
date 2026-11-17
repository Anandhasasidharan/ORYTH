# 🛠️ Development and builds

[← Overview](../README.md) · [Docs index](README.md) · [Contributing](../CONTRIBUTING.md)

## Run from source

Use Python **3.12**, with Tcl/Tk for the desktop window.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe oryth_app.py
```

Linux x64 source mode also works with Tcl/Tk installed. The optional console launcher is:

```bash
python3 scripts/run-local.py
```

The desktop app uses its form and per-user settings. Console mode can read `.env`, copied from [`config/.env.example`](../config/.env.example), or saved settings. Network examples:

```dotenv
NETWORK_PROVIDER=shodan
SHODAN_API_KEY=
MY_PUBLIC_IP=
```

For Censys, select `NETWORK_PROVIDER=censys`, set `CENSYS_TOKEN`, and optionally set `CENSYS_ORGANIZATION_ID`. Never commit real values. Old `HIBP_API_KEY` entries are ignored. Native components download automatically; console mode can reuse a developer runtime through `--runtime <directory>`.

## Tests

```bash
python3 -m pytest -q
python3 tests/smoke_native.py
```

The unit suite uses fixtures and temporary data. The integration test starts actual local services and validates metrics and dashboard queries, with synthetic external provider responses. It can download official runtime components, but does not send your private monitoring targets to the providers.

Packaged validation flags:

```text
ORYTH.exe --check-gui --report <path>
ORYTH.exe --self-test --provider shodan --report <path>
ORYTH.exe --self-test --provider censys --report <path>
```

Recorded v0.3.0 evidence: **99 Windows tests**, both provider modes, and **11 dashboard queries per mode**. See [validation](../VALIDATION.md) and the [build run](https://github.com/Anandhasasidharan/ORYTH/actions/runs/44070440175).

## Build the Windows executable

Build on Windows using Python **3.12 x64**, including Tcl/Tk:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ORYTH.spec
```

The executable is `dist\ORYTH.exe`. To create the ZIP and checksum file, activate that environment and run:

```powershell
.\.venv\Scripts\Activate.ps1
.\packaging\build-windows.ps1
```

Outputs are `dist\ORYTH-Windows-x64.zip` and `dist\SHA256SUMS.txt`.

[`ORYTH.spec`](../ORYTH.spec) bundles the app, Python/Tk dependencies, exporter scripts, and public dashboard templates. Grafana and Prometheus remain independent native components downloaded on first use. Credentials and user data must not be added to build resources.

## Windows workflow and releases

The [workflow](../.github/workflows/windows.yml) runs unit tests, builds the executable, checks the packaged window and provider switching, then tests both network modes against native Windows Grafana/Prometheus. It uploads the ZIP, checksum and diagnostic reports.

A manual `publish` input enables the release job only after the Windows job passes. That job verifies the ZIP checksum before publishing the version pinned in the workflow and packaging metadata. Update version metadata and release notes deliberately for a new release; this is not a general-purpose “publish any version” command.

Keep all Tk widget updates on the GUI thread. Worker threads communicate through the event queue. Maintain process cleanup, backward-compatible settings, provider-neutral metrics, and key-safe error logging.
