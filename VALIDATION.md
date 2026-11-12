# Validation — 2026-11-12

ORYTH now uses the free XposedOrNot email-breach API. No breach API key or paid subscription is required. Existing `.env` values were preserved; an old `HIBP_API_KEY` entry is ignored. Email breach snapshots and metrics use the `xposedornot_` prefix, so historical provider data is not presented as new XposedOrNot results.

## Current results

- Automated suite: **53 passed** (`python3 -m pytest -q -p no:cacheprovider tests`).
- Native stack test: **passed** (`python3 tests/smoke_native.py`).
- Both Python HTTP exporters served metrics successfully.
- Prometheus configuration passed `promtool check config`; both scrape targets were up.
- Synthetic values matched expectations: two ports, two services and four breach matches across two synthetic addresses.
- Grafana database health, datasource connection, provisioned dashboard API and dashboard HTML page passed.
- All **10 dashboard queries** executed successfully through both Prometheus and Grafana's datasource query API.
- Test processes were stopped after validation. Browser visual rendering was not manually inspected.

Native test reports are written under `/tmp/oryth-native-test-*/report.json`. It used synthetic API responses and dummy credentials, with no real user addresses sent externally.

## Live endpoint check

The XposedOrNot public endpoint returned **HTTP 200** for its documented sample address `test@example.com`, with the expected nested breach-name list. Its real response passed the new parser, Prometheus gauge updates and atomic snapshot persistence. Configured personal email addresses were not sent to XposedOrNot during this validation.

No-match responses, HTTP failures, malformed data, rate-limit backoff, unknown-result handling, keyless startup, daily configuration limits, and the 25-attempt rolling-hour scheduler are covered by automated tests. The basic endpoint returns breach names rather than dates, so no days-since-breach metric is emitted. Counts reflect XposedOrNot's database and may differ from other providers.

Earlier authorized Censys checks returned HTTP 200 and exposed an omitted optional `services` field. The parser fix remains covered by four regression cases and was verified against the saved real response. The prior HIBP authentication failure no longer affects the app because that integration has been removed.

## Runtime

Tested directly in WSL/Linux without Docker using Prometheus 3.5.0 and Grafana 12.3.0. Downloaded archives were verified against publisher SHA256 checksums. Binaries are under `/tmp/oryth-native-runtime` and may need downloading again after temporary-file cleanup.

From the project directory:

```bash
python3 scripts/run-local.py
```

Open `http://127.0.0.1:3000/d/oryth-cyber-risk`. Set `MY_EMAILS` in `.env` for daily email checks; see README.md for state-directory and Grafana credential options.

API documentation: https://xposedornot.com/api_doc
