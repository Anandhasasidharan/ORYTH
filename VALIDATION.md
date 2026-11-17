# Shodan Windows preview validation — 2026-11-17

Version 0.3.0 adds Shodan as a selectable network provider, preserves existing Censys settings, and keeps provider keys in per-user configuration rather than in distributed builds. The four-process architecture remains: one selected network exporter, the email exporter, Prometheus and Grafana.

## Local checks

- **99 automated tests passed** after the provider integration, including the existing Windows-backend and monitor coverage.
- New tests cover Shodan response identity and port validation, distinct ports versus service observations, failure-as-unknown behavior, saved snapshots, key-safe error logs, disabled startup, provider selection, legacy settings migration, and credential isolation.
- Provider-neutral dashboard measurements replace Censys-only queries; provider-specific aliases are retained for compatibility.
- The dashboard has **11 queries**, including the selected-provider panel.

## Authorized live checks

The supplied Shodan key authenticated at the account-info endpoint with **HTTP 200**. A separate read-only lookup of Shodan's documented public sample IP returned **HTTP 200**, with two observed ports and three service observations. The parser accepted that real payload. No active scan was submitted, and no personal IP or email address was needed for these checks. The key itself is not included in this document, source, tests, CI or release artifacts.

## Windows release gate — passed

The Windows workflow builds the actual portable executable, verifies desktop-window startup and credential retention across provider switching, and runs isolated synthetic stack tests with **both Shodan and Censys**. Each mode checks all four HTTP services, expected metrics, provider identity, Grafana datasource and dashboard health, all 11 dashboard queries, and process cleanup. Test paths contain spaces.

A manual publish request can create the v0.3.0 preview only after these checks pass and the distribution ZIP checksum is verified on the release runner. Consult the workflow run associated with the release commit for its final result; local tests alone do not establish Windows compatibility.

The v0.2.0 Censys-only release remains available separately. Its earlier Windows validation passed 74 tests and ten dashboard queries. The interview guide describing v0.2.0 should be read as documentation of that earlier version.

## Deployed Windows evidence

[Workflow run 44070440175](https://github.com/Anandhasasidharan/ORYTH/actions/runs/44070440175) completed successfully for commit `6f160c54f1e2199a69bc8baac16071e2d321bd79`:

- All 99 tests passed on Windows.
- The packaged desktop window passed startup and provider-switch key-retention checks.
- Both Shodan and Censys packaged stack tests passed, with real native Windows Grafana and Prometheus processes and synthetic external responses.
- Each provider mode passed all four HTTP endpoints, expected metrics, provider identity, all 11 dashboard queries, and shutdown cleanup.
- The release runner verified the ZIP checksum before publishing v0.3.0.

Published release: https://github.com/Anandhasasidharan/ORYTH/releases/tag/v0.3.0

The release contains no supplied API key. Users select their provider and enter their own credentials locally.
