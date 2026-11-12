# Third-party components

ORYTH uses Python, Tcl/Tk, Requests, prometheus-client, python-dotenv, and the PyInstaller bootloader. Their licenses remain applicable. The executable bundles the Python application and its Python/Tk dependencies; it does not bundle credentials or user settings.

On first start the application downloads unmodified official x64 distributions of:

- Grafana OSS 12.3.0: https://github.com/grafana/grafana (AGPL-3.0)
- Prometheus 3.5.0: https://github.com/prometheus/prometheus (Apache-2.0)

The downloaded archives retain the upstream license and notice files. Publisher SHA256 checksums are verified before extraction. These independent local processes provide the dashboard and metrics database.

XposedOrNot provides the free email-breach API: https://xposedornot.com/api_doc. Network observations come from the optional Censys Platform API: https://docs.censys.com/reference/get-started.
