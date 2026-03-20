# PATCH NOTES — PiBooter 0_1_1

## Summary

This update changes PiBooter from a continuously running onboarding page into the new short-window workflow requested for boot use on Raspberry Pi.

## Requested behaviour implemented

The new runtime now does this:

1. Start hotspot + host web page.
2. Wait **5 seconds** for a hotspot client join or a web request.
3. If nothing arrives, stop hotspot and exit normally.
4. If a phone joins or opens the page, keep PiBooter alive.
5. Let the user enter SSID/password.
6. On successful Wi-Fi join, detect the Pi's router-side IP, save it, and exit.
7. Show that saved **last known router IP** on the hotspot page next time.

## What was changed

### 1. Added startup auto-exit flow

- Added `startup_wait_s` configuration support.
- Added session locking logic so a first client or first HTTP request keeps PiBooter alive.
- Added clean shutdown path that stops the hotspot before normal exit.

### 2. Added persistent last-status storage

- Added new file: `pibooter/status_store.py`
- Added runtime file: `runtime/last_status.json`
- Saved fields now include:
  - last SSID
  - last known Pi IP
  - last known gateway IP
  - hostname
  - update time
  - note text

### 3. Added router-IP capture after successful join

- After successful Wi-Fi connection, PiBooter now polls for the Pi's non-hotspot IP.
- That IP is written into `runtime/last_status.json`.

### 4. Added hotspot client detection

- Added `ip neigh` parsing to detect hotspot clients on the Pi hotspot subnet.
- A joined client can now keep the startup window alive even before the browser fully opens.

### 5. Updated web UI

The page now shows:

- current phase
- startup wait/session state
- hotspot details
- hotspot client list
- nearby Wi-Fi scan cache
- saved Wi-Fi profiles
- recent log
- **last known router-side Pi IP**

### 6. Updated service behaviour

- Changed `systemd` restart mode from `Restart=always` to `Restart=on-failure`
- This prevents endless restarts after normal idle exit or successful completion.

## Likely causes addressed

### Problem: `Restart=always` would have broken the new flow

If PiBooter exited after 5 seconds, systemd would immediately restart it forever.
This patch fixes that by treating idle exit and successful completion as expected behaviour.

### Problem: saved IP needed separate storage

Mixing runtime connection results into the main config file would make the configuration harder to manage and more fragile.
This patch uses a dedicated runtime file instead.

### Problem: short wait windows are easy to miss

A 5-second window is aggressive. To make it more usable, the code now treats both hotspot-client joins and HTTP requests as valid activity.

## Verification performed

The following checks were actually performed:

- Python syntax compiled for the updated PiBooter source files.
- New full project zip was built with the expected PiBooter folder structure.
- Runtime status JSON was included in the package.

## Remaining limitations

- This has not been hardware-tested on your exact Raspberry Pi image.
- `ip neigh` visibility depends on the Pi network stack and timing.
- A 5-second wait is still very short in real use; it is implemented exactly as requested.

## Suggested next improvements

- Add a success splash page that briefly shows the newly saved router IP before shutdown.
- Add optional mDNS/hostname diagnostics.
- Add a stronger captive-portal helper flow for phones that do not auto-open the page.
