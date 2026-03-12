# PATCH NOTES — PiServer_0_1_14

## Summary

This patch removes the web-based update / repo / restart workflow that was added in `0_1_11` to `0_1_13`.

From this patch onward, PiServer is meant to be updated from the terminal with `git pull`, and restarted manually or through `systemd`.

This is a **patch-only** zip and only includes changed files.

## Why this patch was made

The recent web update flow added extra UI and backend complexity:
- `Update` tab
- maintenance mode
- repo checks in the browser
- web-triggered restart flow

In real testing, this made the workflow more fragile than useful. You decided to go back to a simpler and more reliable approach:
- update in terminal
- restart in terminal or with `systemd`
- keep the web UI focused on driving, recording, models, and config

## Main changes

### Removed from the web UI
- `Update` tab removed
- repo status section removed
- `Check repo` button removed
- `Update from Repo` button removed
- `Restart Server` button removed
- update-mode wording removed from the system panel

### Backend changes
- removed web routes for:
  - `/api/system/repo_status`
  - `/api/system/update`
  - `/api/system/restart`
  - `/api/system/maintenance`
- removed app-level use of `UpdateService`
- status payload no longer adds git/restart info

### System panel
- now simplified to:
  - `Save config`
  - `Reload config`
  - message banner
- includes a note telling the user to use `git pull` in terminal instead

## Files changed in this patch

- `PiServer/piserver/app.py`
- `PiServer/piserver/services/__init__.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_14.md`

## Notes about old files already on your Pi

This patch does **not** delete old files automatically.

So if these files already exist from older patches, they may still remain on disk but are no longer used by the patched app:
- `PiServer/piserver/services/update_service.py`

You may leave that file there, or delete it manually later if you want to clean up.

## Validation checklist

After replacing the patch files:

1. Start PiServer normally:

```bash
cd ~/PiDrive/PiServer
python3 server.py
```

2. Confirm the web page shows only these tabs:
- `Manual`
- `Training`
- `Auto`

3. Confirm the System panel no longer has:
- repo controls
- update button
- restart button

4. Confirm these still work:
- algorithm select
- model upload/load
- record toggle
- save config
- reload config
- E-stop

5. Update code from terminal instead:

```bash
cd ~/PiDrive
git pull --ff-only
```

Then restart PiServer manually.

## Expected result

PiServer should now behave more simply and more reliably:
- no web update workflow
- no web restart workflow
- no maintenance tab
- cleaner desktop control UI
- terminal remains the update path
