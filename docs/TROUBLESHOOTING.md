# 🩺 Troubleshooting

[← Overview](../README.md) · [Docs index](README.md) · [Getting started](GETTING_STARTED.md)

Use **Open data folder** and inspect `logs`. Local service readiness and successful external lookups are separate checks.

| Symptom | What to check |
| --- | --- |
| **Port is in use** | Close another ORYTH instance or application using 3000, 9090, 8000 or 8001, then retry. |
| **First start takes time** | Official Grafana and Prometheus binaries must download and pass checksum verification. Later starts reuse the cache. |
| **Download/checksum failed** | Check connectivity and retry Start monitoring. A mismatched archive is rejected before installation. |
| **Shodan 401/403** | Check the selected key and account's host-lookup permission. A valid API key does not always include access to host data. |
| **Censys 401/403** | Check the Platform token, account entitlements and, if needed, organization ID. |
| **Network 404** | The provider may not have a host record. ORYTH reports unknown, rather than zero exposure. |
| **Email lookup 429** | The provider's quota was reached. ORYTH backs off; restarts do not reset a shared upstream quota. |
| **Dashboard loads but results are unknown** | Check enabled status, lookup-success panels, exporter health, and last-success age. |
| **Cannot sign in** | Use username `admin` and the app's Copy password button. Initial settings do not reset an existing Grafana account database. |
| **A displayed result seems old** | Provider observation time can predate ORYTH's lookup. An hourly request does not force a new provider scan. |

## Unknown is not zero

A failed lookup, missing record, disabled integration or malformed response is not a clean security result. Last-success timestamps and old JSON snapshots can remain available while current counts are unknown. Snapshot files are not loaded as new successful results on restart.

For email lookups, only XposedOrNot's explicit documented `{"Error":"Not found"}` result is accepted as no matches; an unrelated 404 is a failure.

## App closed unexpectedly

Inspect `logs` in `%LOCALAPPDATA%\ORYTH`. The manager stops already started child processes after failed startup and cleans up on Stop/close. Scheduled monitoring only continues while the desktop app remains open.

## Reporting a problem

Open a [GitHub issue](https://github.com/Anandhasasidharan/ORYTH/issues) with your app version, Windows version, failing stage, and a sanitized error excerpt.

> [!IMPORTANT]
> Remove API keys, dashboard passwords, personal email addresses, private targets, and sensitive provider results before sharing settings, logs, or screenshots. Do not upload your entire application-data folder.

[Architecture →](ARCHITECTURE.md) · [Privacy and data →](PRIVACY.md)
