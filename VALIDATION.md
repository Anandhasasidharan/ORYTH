# Desktop validation — 2026-11-12

ORYTH 0.2.0 replaces the container setup with a native Windows desktop launcher, per-user settings, automatic verified runtime downloads, local-only services, process cleanup, and portable executable packaging.

## Local checks

- Unit suite: **74 passed** on Linux/WSL, covering monitors, response parsing, settings, archive checksums, unsafe archive paths, cancellation, process rollback, credential isolation, and configuration consistency.
- The synthetic integration test runs the same entry points used by the desktop app, starts real Grafana and Prometheus, checks both exporters, validates expected metric values and all 10 dashboard queries, then stops the services.
- Official Windows runtime archive and checksum URLs returned HTTP 200.

## Windows release checks

The Windows application workflow is the authoritative packaged-executable check. It runs unit tests on Windows, builds `ORYTH.exe`, creates the desktop window, downloads and verifies official Windows Grafana and Prometheus runtimes, and runs the packaged executable's synthetic end-to-end test. Each job saves JSON validation reports and build artifacts.

See the workflow run associated with the release commit for the actual Windows results. Linux tests alone do not establish that a Windows executable works.

## Provider checks from the previous implementation

XposedOrNot returned HTTP 200 for its documented public sample address. The real response passed parsing, metrics and atomic snapshot persistence. Censys returned HTTP 200 during an authorized lookup, and its omitted optional `services` field is covered by regression tests. Configured personal email addresses are not used in automated tests.
