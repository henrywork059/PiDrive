# PiBooter

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
- Password: `pibooter1234`
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

- normalize the config file
- ensure the runtime folder exists
- install the `systemd` service
- enable the service
- restart PiBooter immediately

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
