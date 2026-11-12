# Contributing

Install `requirements-dev.txt` in a virtual environment and run `python -m pytest -q` before submitting a change. Tests must use synthetic data and mocked HTTP responses rather than real accounts or API keys.

Keep credentials in `.env`, which is ignored by Git and excluded from Docker builds. Do not commit personal snapshots from `data/` or `scripts/data/`. Preserve unknown/error states rather than turning unavailable API data into clean security results.

For changes to monitoring or infrastructure, also run `docker compose config --quiet` and, when Docker is available, start the stack and verify both exporter targets from Prometheus and the provisioned dashboard in Grafana.
