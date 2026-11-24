# PiBooter

## R49 — Safe recent Wi-Fi events (0_1_8)

PiBooter's existing `RuntimeState` already bounds its internal log using
the configured `server.log_limit`. Its web UI now displays only an
**allowlisted, sanitized projection**: Wi-Fi scan, connection success/failure,
saved profile removal, hotspot start/stop, setup-window lifecycle and
monitor errors. The page's old raw Recent log is replaced by a collapsed
**Recent operator events (sanitized)** view with **Refresh events** and
**Copy events**. The read-only `GET /api/recent-events` returns at most
**80** events selected from the newest 200 internal log entries. No stored
password, SSID, hotspot key, IP/MAC, connection name, raw nmcli output,
exception text or filesystem path appears in this event export.

This is intentionally a *projection*, not a new storage layer. The
original private/local troubleshooting log, CSRF/origin restrictions,
short startup setup window, existing NetworkManager actions and saved
connection settings remain unchanged. PiBooter **does not control
motors**; safety STOP event logging applies to PiServer/CustomDrive,
not Wi-Fi onboarding. The browser fetch is on-demand when the collapsed
view expands, with an optional Copy; no cloud telemetry or timer.

From repository root:
```bash
cd PiBooter && python -m unittest discover -s tests -p 'test_recent_events_r49.py' -v
cd ..
node --test PiBooter/tests/test_recent_events_ui_r49.cjs
```
Review on a real Pi and confirm Wi-Fi password/SSID/paths are absent from
exported history while scan/connect/failure events remain interpretable.

PiBooter is a Raspberry Pi boot-time Wi-Fi onboarding service.

When the Pi powers on and **does not already have a saved network active**, PiBooter can bring up a local setup hotspot so that you can use a **phone, tablet, or laptop** to tell the Pi which Wi-Fi network it should join.

This version follows the workflow you requested:

1. PiBooter starts at boot.
2. It brings up the hotspot and web page.
3. It waits **5 seconds** for either:
   - a hotspot client to join, or
   - any web request to the setup page.
4. If nothing connects in that 5-second window, PiBooter stops the hotspot and exits.
5. If a phone joins or opens the page in time, PiBooter stays alive.
6. When Wi-Fi setup succeeds, PiBooter reads the Pi's router-side IP, saves it, and exits.
7. The next time the hotspot page appears, it shows the **last known router IP**.

## What PiBooter uses

PiBooter is intentionally lightweight:

- **Python standard library only** for the web UI and background service logic
- **`nmcli` / NetworkManager** for Wi-Fi scanning, hotspot control, and saving Wi-Fi profiles
- **`systemd`** so it can start automatically on boot

## Folder layout

```text
PiBooter/
├── README.md
├── requirements.txt
├── install.sh
├── run_pibooter.py
├── config/
│   └── settings.json
├── runtime/
│   └── last_status.json
├── boot/
│   └── pibooter.service
├── pibooter/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── network.py
│   ├── state.py
│   └── status_store.py
└── PATCH_NOTES/
```

## Important requirement

PiBooter expects **NetworkManager / `nmcli`** to be available.

This project does **not** reconfigure older `wpa_supplicant`-only setups into a hotspot by itself.
If `nmcli` is missing, the web page can still start, but PiBooter cannot:

- scan Wi-Fi networks
- create the setup hotspot
- save Wi-Fi credentials
- switch the Pi onto the chosen Wi-Fi

## Default setup hotspot

By default PiBooter uses:

- SSID: `PiBooter-<hostname suffix>`
- Password: a unique 32-character randomly generated WPA2 passphrase, provisioned locally per Pi
- Setup page: `http://192.168.4.1/`
- Startup wait window: `5 seconds`

You can change these values in:

```text
PiBooter/config/settings.json
```

## Install on the Pi

```bash
cd ~/PiDrive/PiBooter
chmod +x install.sh
sudo ./install.sh
```

That script will:

- normalize the config file and replace the publicly known example hotspot passphrase with a random per-device credential while **preserving existing custom passwords**
- tighten configuration file permissions and print the new credential only when run from an interactive terminal
- ensure the runtime folder exists
- install the `systemd` service
- enable the service
- restart PiBooter immediately

## Secure provisioning and recovery (0_1_3)

**First install:** run `install.sh` from the Pi's own terminal. When the
checked-in example password is present, the installer generates a fresh,
unique 32-character WPA2 passphrase and stores it in the existing settings
file. It **does not rotate** a password that you already customized. On a
brand-new missing config file, a unique password is generated automatically.
The file contains sensitive material and the installer restricts its
permissions to `0600` (owner only). Keep local changes to
`PiBooter/config/settings.json` private: do not commit the provisioned
password to GitHub or share it in logs/screenshots.

To read the current password from the Pi's **local private terminal**:

```bash
cd ~/PiDrive/PiBooter
sudo python3 run_pibooter.py --config config/settings.json --show-hotspot-password
```

To provision the published example while keeping any existing custom password:

```bash
sudo python3 run_pibooter.py --config config/settings.json --provision-hotspot-password
```

To **explicitly rotate** any current hotspot password (devices must reconnect):

```bash
sudo python3 run_pibooter.py --config config/settings.json --rotate-hotspot-password
sudo systemctl restart pibooter.service
```

A legacy installation retaining the publicly known default is **not allowed to
start or continue serving the setup hotspot**. Provision a private passphrase
locally, then restart the service. If settings are malformed, the prior
`0_1_2` configuration recovery behavior remains: the original file is
preserved, and provisioning refuses to replace it until repaired.

**Web security:** the setup page no longer displays the hotspot passphrase,
nor does `/api/status` return it. Network-changing `/connect`,
`/forget`, and `/rescan` requests require an unguessable token
from the live setup page and must originate from the Pi itself or a client
on the configured setup-hotspot subnet. Cross-origin posts are rejected;
read-only `/api/networks` no longer triggers an active rescan.
A normal phone browser form automatically includes the token.

The five-second first-client window, NetworkManager handover and saved router
IP flow are unchanged. Because PiBooter is served over plain HTTP, avoid
forwarding its port onto untrusted networks. A device that already knows the
Wi-Fi hotspot passphrase can still request a setup token; these protections
do not provide an additional login barrier. For full resistance to local
compromise, use an isolated physical setup network and consider a separate
operator approval or HTTPS/VPN. NetworkManager may pass credentials in local
process arguments; protecting local process inspection remains follow-up work.

## Onboarding status and failure recovery (0_1_4)

The phone setup page now uses the backend's **read-only onboarding status**,
alongside its existing network/runtime details:

- **Scanning nearby Wi-Fi:** a refresh scan is in progress. Some adapters cannot
  rescan while hosting a hotspot; manually enter the SSID if it is absent.
- **Connecting to Wi-Fi:** one connection request is in progress. Wait for the
  NetworkManager handover; your phone may briefly lose the PiBooter hotspot.
- **Connected to Wi-Fi:** reconnect your phone to the router network; use the
  saved *last known* IP or locate the current Pi address from your router.
  PiBooter exits normally after completing setup.
- **Wi-Fi setup failed:** if the setup hotspot has returned, rejoin it, verify
  the SSID/password and submit again; the failed password is **not** retained
  by the form. If the hotspot cannot be restored, restart PiBooter locally,
  or reboot the Pi, to open a fresh setup session.
- **Setup window closing:** no eligible first client has activated the
  configured short startup window. PiBooter stops the hotspot and exits; the
  page does not extend the window automatically.

**Do not change** the configured `server.startup_wait_s` merely to keep the
hotspot open: the normal first-client policy remains the default **5 seconds**,
and the page polls only to report state. The status API adds a credential-free
`onboarding` object with `state`, `headline`, `summary`,
`next_action` and remaining-window information; existing API fields stay
available. Invalid public hotspot credentials still require local
`--provision-hotspot-password` as described above.

The normal launch entry point remains
`cd ~/PiDrive/PiBooter && sudo python3 run_pibooter.py --config config/settings.json`.
For optional offline checks run
`python3 -m unittest discover -s tests -p 'test_onboarding_status.py' -v`.
This web guidance does not test real Wi-Fi reception or servo/motor hardware.

## Keyboard and low-motion setup (0_1_5)

The PiBooter phone setup page can also be used from a keyboard: press
**Tab** to move among Wi-Fi names, Connect, Refresh scan, Clear password and
saved-network actions, then use **Enter** or **Space** as supported by the
native focused button. **Skip to setup** appears when keyboard-focused and
moves past the page header directly into the setup landmark.

Buttons for nearby networks now include the chosen SSID in their accessible
name; Forget buttons include the stored profile name to avoid ambiguous
repeated announcements. A visible keyboard focus ring, high-contrast fallback
and reduced-motion scrolling are provided. These changes do not create
keyboard shortcuts to alter Wi-Fi, relax hotspot security, or lengthen the
original short first-client window.

## Phone-width Wi-Fi results (0_1_6)

At phone widths, the Wi-Fi scan table keeps **Use this network** available
in its rightmost action column. Scan Channel and the device connection column
can be hidden on narrow screens, but the network selection action is never
hidden. If the network list is wider than the card, swipe horizontally within
the labelled network-results region (or focus the region and scroll using
keyboard controls). Saved-profile **Forget** controls use a similar scrollable
table; existing CSRF and Wi-Fi setup authorization still apply.

To review viewport reachability on an **authorized test setup**, see
`PiServer/tests/R36_VIEWPORT_MATRIX.md` and the Playwright runner there.
Visiting PiBooter from an authorized hotspot client can activate the existing
first-client setup session. The default five-second session window is
unchanged.

## Manual run

```bash
cd ~/PiDrive/PiBooter
sudo python3 run_pibooter.py --config config/settings.json
```

## Using it from your phone

### Case 1: Pi has no saved network active

PiBooter should start the hotspot automatically.

1. Join the hotspot on your phone.
2. If your phone warns that there is no internet, stay connected anyway.
3. Open:

```text
http://192.168.4.1/
```

4. Choose a nearby SSID from the list or type it manually.
5. Enter the Wi-Fi password and submit.
6. Wait while the Pi switches away from hotspot mode and joins your selected Wi-Fi.
7. Reconnect your phone to the same router Wi-Fi and browse to the **saved last known Pi IP** shown on the page from the previous successful connection, or try `hostname.local`.

### Case 2: Pi is already reachable on Ethernet or Wi-Fi

PiBooter still starts briefly, but if nobody opens it within 5 seconds it exits normally.

## Saved status file

PiBooter saves the last successful router-side connection here:

```text
PiBooter/runtime/last_status.json
```

That file stores:

- last SSID
- last known Pi IP
- last known gateway IP
- hostname
- last update timestamp
- a note explaining that DHCP may change the IP later

## Notes and limitations

### 1. The wait window is intentionally short

You requested a **5-second** first-client wait.

To make that workable, PiBooter stays alive when **either** of these happens during startup:

- a hotspot client joins, or
- the web page receives a request

### 2. Single-radio scanning while hotspot is active

Many Raspberry Pi Wi-Fi adapters cannot do a full fresh scan while they are actively hosting an access point.
PiBooter keeps a cached scan list and also gives you a manual SSID field for this reason.

### 3. Root privileges

The included `systemd` service runs as root so PiBooter can manage NetworkManager profiles and switch network modes.
Keep PiBooter on trusted local networks only.

### 4. Captive portal behaviour

PiBooter includes a few common captive-portal probe endpoints and tries to behave nicely with phones, but this is **not** a full DNS-hijacking captive portal implementation.
If the setup page does not open automatically, browse to the hotspot URL manually.

### 5. Successful exits are normal now

The service now uses `Restart=on-failure`.

That matters because PiBooter is **supposed** to exit normally when:

- nobody connects during the 5-second wait, or
- Wi-Fi setup succeeds and the last known IP is saved

## Configuration recovery

If `config/settings.json` is malformed or has an invalid section structure, PiBooter **does not overwrite it**. It runs with in-memory defaults for diagnosis, shows a recovery warning in its web page and logs, and tries to save a separate `settings.json.corrupt-<hash>` copy next to the original. Repeated starts with the same invalid file reuse the existing recovery copy.

To repair, stop PiBooter and fix or restore `config/settings.json` manually before restarting. Programmatic `ConfigStore.save()` refuses to overwrite an invalid original unless explicitly called with `replace_invalid=True`; do not use this option without a known-good backup. Missing settings files are created as before, and valid saved settings are retained with missing defaults filled safely.

## Quick troubleshooting

### Check the service

```bash
sudo systemctl status pibooter.service
journalctl -u pibooter.service -n 100 --no-pager
```

### Check NetworkManager

```bash
nmcli general status
nmcli device status
```

### Restart PiBooter manually

```bash
sudo systemctl restart pibooter.service
```

### Stop PiBooter temporarily

```bash
sudo systemctl stop pibooter.service
```
