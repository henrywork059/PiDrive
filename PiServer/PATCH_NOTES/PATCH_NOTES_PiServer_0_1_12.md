# PATCH NOTES — PiServer 0_1_12

Base for this patch: PiServer 0_1_11
Patch type: patch-only zip with changed/new files only

## Goal
Make the web restart flow reliable and simple to validate after using `Update from Repo`.

## Main changes
- kept the `0_1_11` repo update feature intact
- changed `Restart Server` so it re-launches the current PiServer process directly
- restart no longer depends on calling `systemctl restart` from inside the web request
- restart now works when PiServer is started manually with `python3 server.py`
- `/api/status` now includes restart state so the UI can show pending restart status
- the browser now disables the restart button while a restart is pending
- the browser waits for PiServer to come back and shows a reconnect message
- Git update messages now report whether the commit changed and remind you to restart when needed

## Why this patch was needed
In `0_1_11`, repo update could work, but the restart path still depended on `systemctl restart`. That can fail when PiServer is not running under a service with the required permissions, and it is harder to validate during development when launching with `python3 server.py`.

## Files changed
- `PiServer/piserver/services/update_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_12.md`

## Validation steps
1. Start PiServer normally from your repo-backed folder:
   `cd /home/pi/PiDrive/PiServer && python3 server.py`
2. Open the web UI and click `Check repo`
3. Click `Restart Server`
4. Confirm the button changes to `Restarting…`
5. Confirm the page reconnects within a few seconds
6. Make a small commit to GitHub
7. Click `Update from Repo`
8. Confirm the message shows the old and new commit IDs
9. Click `Restart Server` again to load the new code

## Notes
- update still requires a real Git checkout such as `/home/pi/PiDrive/PiServer`
- if the browser does not reconnect automatically after restart, refresh the page once
