# 🚀 Getting started

[← Overview](../README.md) · [Docs index](README.md) · [Troubleshooting](TROUBLESHOOTING.md)

## What you need

- Windows **10 or 11, x64**.
- Internet for first-run component downloads and ongoing provider lookups.
- Space for the downloaded components, local databases, and logs.
- No separate Python installation, WSL, administrator installation, or Windows service setup.

The Windows executable is currently an **unsigned desktop preview**. It is distributed as a ZIP, not a system installer.

## Download and open

1. Open [Releases](https://github.com/Anandhasasidharan/ORYTH/releases).
2. Download `ORYTH-Windows-x64.zip` and extract it into a folder you own.
3. Open `ORYTH.exe`.

`SHA256SUMS.txt` is supplied with the release if you want to compare the ZIP's checksum. The application separately verifies its own first-run runtime downloads before extracting them.

## Choose your monitoring options

### 🟢 Email monitoring

Enter addresses separated by commas or new lines. ORYTH normalizes and deduplicates them, then checks them through [XposedOrNot](https://xposedornot.com/api_doc).

No breach API key is needed. The implementation accepts at most 100 unique addresses per daily cycle, spaces requests, limits attempts to 25 per rolling hour, and honors rate-limit backoff. Other clients using your public IP and repeated restarts share the provider's quota.

### 🔵 Optional network monitoring

Select a provider and enter **both** your public IP and the selected credential:

| Provider | Credential | Notes |
| --- | --- | --- |
| **Shodan** | Your own Shodan API key | The account must permit host lookups. A key alone does not guarantee that permission. |
| **Censys** | Your Censys Platform token | Account entitlements apply. An organization ID is optional. |

Switching providers retains the credential entered for each provider. Existing Censys settings retain Censys as their selected provider after upgrading. Leave the selected provider's key and public IP blank for email-only use.

> [!IMPORTANT]
> No shared provider key is shipped with ORYTH. Enter your own credentials locally. Do not paste keys into GitHub issues or screenshots.

## Start and sign in

1. Click **Start monitoring**.
2. On first use, allow the official Grafana and Prometheus downloads and checksum checks to complete. Subsequent starts reuse cached components.
3. Click **Copy password**.
4. Click **Open dashboard**.
5. Sign in as **`admin`**, using the copied password.

The password is generated and saved with your local settings. Changing an initial password setting does not reset an existing Grafana database account.

## Everyday use

- Keep the desktop window open while monitoring.
- Use **Stop** to end monitoring. Closing the app also stops its four local processes.
- Use **Open data folder** to inspect settings, snapshots, logs, and databases.
- Check the dashboard's **lookup status** and **last-success age**, not only its counts.

Network lookups run roughly hourly, email cycles roughly daily, and Prometheus reads local measurements every 15 seconds. A recently refreshed dashboard can still show an older provider observation.

The dashboard normally opens at `http://127.0.0.1:3000/d/oryth-cyber-risk`.

[Privacy and data →](PRIVACY.md) · [Startup help →](TROUBLESHOOTING.md)
