<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/hero-light.svg">
  <img alt="ORYTH — Personal Cyber Exposure Dashboard for Windows" src="docs/assets/hero-light.svg" width="100%">
</picture>

### Known exposure. One local dashboard.

Free email-breach checks, optional Shodan or Censys observations, and clear monitoring health — managed from a Windows desktop app.

[![Windows build](https://img.shields.io/github/actions/workflow/status/Anandhasasidharan/ORYTH/windows.yml?branch=main&style=for-the-badge&label=Windows%20build)](https://github.com/Anandhasasidharan/ORYTH/actions/workflows/windows.yml)
[![Latest preview](https://img.shields.io/github/v/release/Anandhasasidharan/ORYTH?include_prereleases&style=for-the-badge&color=8B5CF6&label=Latest%20preview)](https://github.com/Anandhasasidharan/ORYTH/releases)
[![Downloads](https://img.shields.io/github/downloads/Anandhasasidharan/ORYTH/total?style=for-the-badge&color=0891B2)](https://github.com/Anandhasasidharan/ORYTH/releases)

![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011%20x64-0078D4?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/Desktop-Tkinter-0D9488?style=flat-square)
![Prometheus](https://img.shields.io/badge/Metrics-Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Dashboard-Grafana-F46800?style=flat-square&logo=grafana&logoColor=white)

[![Download Windows app](https://img.shields.io/badge/Download-Windows%20app-7C3AED?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Anandhasasidharan/ORYTH/releases)
[![Read the quick start](https://img.shields.io/badge/Read-Quick%20start-0284C7?style=for-the-badge&logo=readthedocs&logoColor=white)](docs/GETTING_STARTED.md)

[Features](#-what-you-get) · [Quick start](#-start-here) · [Architecture](#-how-data-moves) · [Documentation](#-explore-the-docs) · [Validation](#-verified-windows-preview)

</div>

> [!TIP]
> **No Python, WSL, or container setup required for the Windows download.** Extract the ZIP, open `ORYTH.exe`, and enter your settings. First start downloads and verifies the dashboard components.

## ✨ What you get

| | Feature | What it does |
| :---: | --- | --- |
| 🟢 | **Email breach exposure** | Free, keyless daily checks with XposedOrNot. View per-address counts and a complete total when all lookups succeed. |
| 🔵 | **Your choice of network provider** | Select Shodan or Censys for hourly lookups of recorded ports and services on your public IP. |
| 🟣 | **Monitoring you can inspect** | See which provider is selected, whether checks succeeded, and how old the last successful result is. |
| 🟠 | **A local dashboard** | Prometheus records measurements; Grafana displays them. Both listen on your own computer. |
| 🟢 | **Desktop control** | Start, stop, prepare components, copy the dashboard password, and open your data folder from one window. |
| 🔵 | **Honest failure states** | Failed lookups stay unknown. Unavailable data is never silently reported as zero exposure. |

## 🚀 Start here

1. Download **`ORYTH-Windows-x64.zip`** from [Releases](https://github.com/Anandhasasidharan/ORYTH/releases).
2. Extract the ZIP and double-click **`ORYTH.exe`**.
3. Enter the email addresses you want to monitor. Network monitoring is optional: select **Shodan** or **Censys**, then enter your public IP and your own provider credential.
4. Click **Start monitoring** and allow first-run component preparation to finish.
5. Click **Copy password**, then **Open dashboard**. Sign in as **`admin`** with the copied password.

**Windows 10/11 x64 · Internet required · Keep the app window open while monitoring**

The executable is an unsigned preview. Closing it stops the local services. [Full setup guide →](docs/GETTING_STARTED.md)

## 🧭 How data moves

```mermaid
flowchart LR
    X["XposedOrNot<br/>Known email breaches"] --> E["Python email exporter"]
    S["Shodan or Censys<br/>Recorded host observations"] --> N["Python network exporter"]
    E --> P["Prometheus<br/>Metrics and history"]
    N --> P
    P --> G["Grafana<br/>Local dashboard"]
    A["ORYTH Windows app<br/>Configure · start · stop"] -. "manages local services" .-> P

    classDef email fill:#065f46,stroke:#34d399,color:#ffffff;
    classDef network fill:#164e63,stroke:#22d3ee,color:#ffffff;
    classDef metrics fill:#5b21b6,stroke:#c4b5fd,color:#ffffff;
    classDef view fill:#9a3412,stroke:#fdba74,color:#ffffff;
    classDef app fill:#1e293b,stroke:#94a3b8,color:#ffffff;
    class X,E email;
    class S,N network;
    class P metrics;
    class G view;
    class A app;
```

The arrows show data flow. Prometheus **pulls** metrics from the exporters every **15 seconds**; provider lookups run roughly **hourly** for network data and **daily** for email data. The desktop app manages all four local processes. [Architecture and timing →](docs/ARCHITECTURE.md)

> [!NOTE]
> ORYTH reads existing provider records. It does **not** submit active scans, predict attacks with AI, or guarantee that an address is safe when no matching data is found.

## 📚 Explore the docs

| Guide | What you will find |
| --- | --- |
| [🚀 Getting started](docs/GETTING_STARTED.md) | Windows setup, credentials, first-run downloads, and everyday use |
| [🧩 Architecture](docs/ARCHITECTURE.md) | Components, schedules, process lifecycle, metrics, and source-code map |
| [🛠️ Development](docs/DEVELOPMENT.md) | Source setup, Windows builds, tests, and release automation |
| [🔒 Privacy and data](docs/PRIVACY.md) | Which providers receive data, local storage, credentials, and limitations |
| [🩺 Troubleshooting](docs/TROUBLESHOOTING.md) | Startup, port conflicts, download issues, authentication, and unknown results |
| [✅ Validation record](VALIDATION.md) | Recorded Windows test and release evidence |
| [🤝 Contributing](CONTRIBUTING.md) | Development practices and safe test data |
| [📦 Third-party components](THIRD_PARTY.md) | Runtime components, sources, and licenses |

## ✅ Verified Windows preview

The [v0.3.0 build](https://github.com/Anandhasasidharan/ORYTH/actions/runs/44070440175) passed:

| Automated tests | Packaged provider modes | Dashboard queries per mode |
| :---: | :---: | :---: |
| **99 passed on Windows** | **Shodan + Censys** | **11 passed** |

The workflow also checked packaged desktop startup, provider-switch credential retention, expected synthetic metrics, native Grafana/Prometheus startup, cleanup, and the distribution checksum. These are recorded release results; the build and release badges above update independently.

<details>
<summary><strong>Why does the app download Prometheus and Grafana?</strong></summary>

Prometheus stores numerical measurements over time. Grafana turns them into the dashboard. The desktop app downloads their official binaries on first start, verifies publisher SHA256 checksums, and reuses them later. [Details →](docs/ARCHITECTURE.md#the-two-dashboard-components)

</details>

<details>
<summary><strong>Do I need a paid API key?</strong></summary>

Email checks use the free XposedOrNot endpoint without a key. Network monitoring is optional and requires your own provider credential. Shodan host lookup requires suitable account access; having a key alone may not grant it. Censys access depends on the account's entitlements. [Provider setup →](docs/GETTING_STARTED.md#choose-your-monitoring-options)

</details>

<details>
<summary><strong>Where are my settings and results stored?</strong></summary>

Under `%LOCALAPPDATA%\ORYTH` for your Windows account. Provider credentials are not bundled in the app or CI, but settings are not encrypted by this implementation. Email addresses and the selected network target are sent to their respective providers when monitoring starts. [Privacy details →](docs/PRIVACY.md)

</details>

---

<div align="center">

**Understand what is known. See when a check fails. Stay in control of your monitoring.**

[Download](https://github.com/Anandhasasidharan/ORYTH/releases) · [Read the docs](docs/README.md) · [Report an issue](https://github.com/Anandhasasidharan/ORYTH/issues)

</div>
