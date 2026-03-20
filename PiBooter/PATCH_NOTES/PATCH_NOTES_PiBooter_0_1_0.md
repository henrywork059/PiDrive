# PATCH NOTES — PiBooter 0_1_0

## Summary

Initial release of a new `PiDrive/PiBooter` project.

PiBooter adds a boot-time Wi-Fi onboarding flow for Raspberry Pi so the Pi can expose a temporary setup hotspot and let a user connect it to home Wi-Fi from a phone, tablet, or laptop.

## Problem this project is solving

A headless Pi is awkward to deploy when the user does not yet know the Pi’s IP address and cannot easily connect a monitor/keyboard.

The user asked for a project that:

- runs automatically when the Pi powers on
- helps the user connect the Pi to Wi-Fi
- is usable from a phone or other nearby device

## Design chosen

PiBooter uses:

- Python standard library for the web server and runtime state
- NetworkManager / `nmcli` for Wi-Fi scan, hotspot, connect, and saved profile management
- `systemd` for auto-start on boot

Why this design:

- it avoids adding heavy Python dependencies
- it matches Raspberry Pi’s current `nmcli`-based hotspot workflow
- it keeps the project easy to inspect, patch, and debug later
- it lets the temporary hotspot remain separate from the main PiServer runtime

## Files added

### New project

- `PiBooter/README.md`
- `PiBooter/requirements.txt`
- `PiBooter/install.sh`
- `PiBooter/run_pibooter.py`
- `PiBooter/config/settings.json`
- `PiBooter/boot/pibooter.service`
- `PiBooter/pibooter/__init__.py`
- `PiBooter/pibooter/app.py`
- `PiBooter/pibooter/config.py`
- `PiBooter/pibooter/network.py`
- `PiBooter/pibooter/state.py`
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_0.md`

### Repo docs updated

- `README.md`
- `INSTRUCTIONS.md`

## Core behaviour in this release

### 1. Boot-time web service

PiBooter includes a `systemd` unit template and an install script so it can start automatically after boot.

### 2. Temporary setup hotspot

If the Pi does not already have an active saved network, PiBooter can create a hotspot profile and bring it up through NetworkManager.

Default values:

- hotspot SSID prefix: `PiBooter`
- hotspot password: `pibooter1234`
- setup URL: `http://192.168.4.1/`

### 3. Phone-friendly setup page

The web UI shows:

- current network state
- nearby Wi-Fi scan results
- a manual SSID entry form
- saved Wi-Fi profiles
- a recent runtime log

### 4. Save and join selected Wi-Fi

When a user submits Wi-Fi details, PiBooter:

- stops the temporary hotspot
- asks NetworkManager to connect to the chosen SSID
- marks the saved network as autoconnect
- raises its autoconnect priority above the hotspot profile
- restores the hotspot if the Wi-Fi join fails

### 5. Safer fallback behaviour

If `nmcli` is missing, PiBooter does not crash blindly.
It still shows a page and reports that NetworkManager is required for hotspot/Wi-Fi control.

## Robustness work included in the first release

- config file is normalized and rewritten safely with defaults filled in
- hotspot password is clamped to a valid WPA length range
- `nmcli` command errors are captured and surfaced in the UI/log
- connection attempts run in a background thread so the page stays responsive
- hotspot is automatically restored after failed Wi-Fi connection attempts
- scan results are cached because many single-radio Pi Wi-Fi adapters cannot do reliable rescans while hosting an AP
- common captive-portal probe paths are handled so phones are less likely to show a blank failure page

## Documentation added

The new README includes:

- install steps
- direct-run steps
- phone usage instructions
- troubleshooting commands
- limitations and behaviour notes

## Verification performed

The following checks were performed locally on the generated code package:

- Python syntax compilation for the new `PiBooter/` package
- import smoke test for the main entrypoint module
- packaging check to ensure the new project folder and patch notes are included

## Not verified here

The following require a real Raspberry Pi / Raspberry Pi OS environment and were not claimed as already field-tested here:

- real hotspot creation on the target Pi Wi-Fi chipset
- real phone/browser captive-portal behaviour on iOS/Android
- real switching from hotspot mode to a home router SSID on the target image
- NetworkManager presence/configuration on the user’s exact Pi OS image

## Future improvements that would make sense next

- optional full captive portal DNS interception
- QR code output for hotspot details
- optional bridge mode when Ethernet is present
- onboarding completion page that reports the new IP more explicitly
- optional hostname / mDNS guidance widget
- optional small OLED / LCD output for setup SSID and password
