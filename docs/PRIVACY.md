# 🔒 Privacy and data

[← Overview](../README.md) · [Docs index](README.md) · [Architecture](ARCHITECTURE.md)

## Which services receive data?

Monitoring begins when you click **Start monitoring**.

| Destination | Data sent | Purpose |
| --- | --- | --- |
| `api.xposedornot.com` | Configured email addresses | Known email-breach lookups |
| `api.shodan.io` | Configured public IP and Shodan key, when selected | Read existing Shodan host observations |
| `api.platform.censys.io` | Configured public IP and Censys token, when selected; optional organization ID | Read existing Censys observations |
| Official runtime download hosts | Ordinary HTTPS download requests | Obtain Grafana and Prometheus on first start |

Only the selected network provider's credential is passed into the service environment. Email monitoring does not require either network provider.

## Where data is stored

On Windows:

```text
%LOCALAPPDATA%\ORYTH
├── settings.json       User configuration and credentials
├── runtime\            Cached native components
├── provisioning\       Generated local configuration
├── snapshots\          Last successful provider results
├── logs\               Local service logs
├── prometheus-data\    Time-series history
└── grafana-data\       Grafana application/account database
```

The app's **Open data folder** button opens this directory. On Linux, source mode uses the user's XDG data location or `~/.local/share/oryth`.

> [!IMPORTANT]
> Local storage is **not encryption**. This implementation does not encrypt settings with Windows Credential Manager or DPAPI. Treat the application-data folder as sensitive.

## Credential and logging behavior

- Each user supplies their own keys locally. Keys are not bundled in the executable, repository, release archive, or CI fixtures.
- Shodan transmits its key as an HTTPS query parameter. Failed Shodan calls log status and exception class, rather than URLs, response bodies, or exception text that might include the key.
- Source-mode `.env` files, settings, caches and personal snapshots are excluded from Git. Build resources include only selected scripts and public configuration.
- The dashboard password is generated for the local account and saved with settings.

Email snapshot filenames hash the normalized full address. That avoids unsafe filenames and collisions; it is not anonymization. Metrics still contain email labels, and guessing a known address can reproduce its filename hash.

## Local access and limits

Services bind to `127.0.0.1`, on ports 3000, 9090, 8000 and 8001. They are intended for the local computer, not as a public hosted service. Local binding does not protect against another process or user with sufficient access to the same machine.

A breach match means the provider has a known record. A no-match result is not proof that no breach occurred. Publicly visible ports are not automatically vulnerabilities. A configured public IP can represent a shared router or hosting environment, rather than one laptop.

Closing the application stops monitoring. There is no always-running Windows service or automatic email-alert feature in this release.
