# Desktop validation — 2026-11-12

ORYTH 0.2.0 replaces the container setup with a native Windows desktop launcher, per-user settings, automatic verified runtime downloads, local-only services, process cleanup, and portable executable packaging.

## Local checks

- Unit suite: **74 passed** on Linux/WSL, covering monitors, response parsing, settings, archive checksums, unsafe archive paths, cancellation, process rollback, credential isolation, and configuration consistency.
- The synthetic integration test runs the same entry points used by the desktop app, starts real Grafana and Prometheus, checks both exporters, validates expected metric values and all 10 dashboard queries, then stops the services.
- Official Windows runtime archive and checksum URLs returned HTTP 200.

## Windows release checks — passed

[Windows build 43146547261](https://github.com/Anandhasasidharan/ORYTH/actions/runs/43146547261) passed on commit `5fda49e9c6335fa481e1afbbdb7019b05bf1e415`:

- All **74 unit tests passed on Windows**.
- PyInstaller built the portable Windows x64 executable successfully.
- The packaged executable created and ran its desktop window event loop successfully.
- The packaged application downloaded and checksum-verified the official native Windows Grafana and Prometheus runtimes.
- All four local HTTP services became healthy.
- Expected synthetic values arrived in Prometheus: two ports, two services, and four email breach matches.
- Grafana dashboard provisioning, datasource health and the dashboard HTML page passed.
- All **10 dashboard queries passed** through both Prometheus and Grafana.
- Service shutdown and cleanup passed.
- Test data paths contained spaces to exercise common Windows user-folder paths.

The first Windows run exposed a missing Grafana SQLite parent directory. Startup now creates all service data folders explicitly, with regression coverage. The corrected build passed in full. The workflow retains JSON test reports and distributable artifacts. This is automated packaged-app validation; no claim is made about manual visual review or every Windows hardware configuration.

## Provider checks from the previous implementation

XposedOrNot returned HTTP 200 for its documented public sample address. The real response passed parsing, metrics and atomic snapshot persistence. Censys returned HTTP 200 during an authorized lookup, and its omitted optional `services` field is covered by regression tests. Configured personal email addresses are not used in automated tests.
