Download **ORYTH-Windows-x64.zip**, extract it and open **ORYTH.exe**.

This preview adds **Shodan network monitoring** while retaining Censys compatibility. Select Shodan or Censys, enter your public IP and your own provider key/token, and click Start monitoring. Email checks remain free through XposedOrNot. No shared provider credentials are included in the app or repository.

- Hourly lookups read existing provider observations; no active or on-demand scans are requested.
- The dashboard uses provider-neutral measurements and shows the selected network data source.
- Existing Censys user settings migrate without losing their provider or token.
- Failed or unindexed lookups remain unknown rather than zero exposure.
- Shodan errors omit URLs, exception text and bodies to protect query-string API keys.
- The Windows workflow tests the packaged GUI and runs the full synthetic stack with both network providers before publishing this release.

Windows 10/11 x64. No Python, WSL, containers or administrator installation is required. First start downloads and verifies official Grafana and Prometheus components. The executable is unsigned. Keep the desktop window open while monitoring.

**Each user must supply their own Shodan API key or Censys token.** Shodan host lookup requires appropriate account access; a free API key alone may not grant it. Local settings are stored under `%LOCALAPPDATA%\ORYTH` and are not encrypted by this implementation.

Sign in to the local dashboard as **admin** using the app's **Copy password** button. Settings, logs and metrics remain in your user profile.

See the [Windows workflow](https://github.com/Anandhasasidharan/ORYTH/actions/workflows/windows.yml) and [README](https://github.com/Anandhasasidharan/ORYTH#readme) for validation and setup.
