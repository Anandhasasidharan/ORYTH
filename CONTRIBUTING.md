# Contributing

Use Python 3.12 or later. Install `requirements-dev.txt` in a virtual environment and run `python -m pytest -q` before submitting a change. Unit tests must use synthetic responses and temporary directories, rather than real accounts or API keys.

Desktop code lives under `oryth/`. `oryth_app.py` starts the window or a packaged exporter worker. Windows builds use PyInstaller and `ORYTH.spec`; no container tooling is used. The Windows workflow validates the actual packaged executable, its Tk window, the official native runtime downloads, and all dashboard queries.

Use `python tests/smoke_native.py` for a local integration test with synthetic data. Keep all Tk calls on the UI thread and clean up every child process on stop, failed startup, and cancelled setup.

Keep credentials out of source, build artifacts, and logs. Desktop settings belong under the user's application-data directory. `.env` is optional for source-mode console use only. Preserve unknown/error states rather than turning unavailable API data into clean security results. Do not commit personal snapshots, local settings, downloaded runtimes, or build output.
