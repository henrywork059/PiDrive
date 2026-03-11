# PATCH NOTES — PiServer_0_1_11

## Goal
Make the base PiServer build able to update code from the GitHub repo when PiServer is running inside the `PiDrive` repository on the Pi.

## Base used
- User-provided PiServer base zip (current working baseline / base 0_1_0 behavior)

## Problem
The base build already had an **Update from Git** button, but the backend only looked for `.git` inside the `PiServer` folder itself.
In the real repo layout, PiServer lives at a subfolder like:
- `/home/pi/PiDrive/PiServer`

That means the real `.git` folder is at:
- `/home/pi/PiDrive/.git`

So the base update logic reported that PiServer was not a Git repo and could not pull updates from GitHub.

## Changes made

### 1) Parent-repo discovery for Git
Updated `piserver/services/update_service.py` to:
- search the current folder and all parent folders for Git metadata
- detect when PiServer is running inside a parent repo
- run Git commands from the true repo root
- report:
  - repo root
  - project directory
  - relative project path inside the repo
  - branch
  - commit
  - remote URL
  - dirty status

### 2) Safer Git update behavior
`git pull --ff-only` now runs from the detected repo root.
This patch also blocks update if Git has local modified files, because a pull would often fail or create a confusing state.

### 3) Repo status API
Added:
- `GET /api/system/repo_status`

This allows the UI to explicitly check repo status on demand.

### 4) Small UI update in the existing System panel
Updated the base UI to add:
- **Check repo** button
- clearer repo status text
- remote / repo path details
- button label changed to **Update from Repo**

### 5) Service file updated for repo-backed install
Updated `boot/pi_server.service` to point at:
- `/home/pi/PiDrive/PiServer`
- `/usr/bin/python3`

This matches the intended no-venv repo-backed setup.

### 6) README updated
Added repo-backed setup instructions for the Git update flow.

## Files changed
- `PiServer/piserver/services/update_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/boot/pi_server.service`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_11.md`

## Validation performed
- Python compile check passed for the patched backend files
- JavaScript syntax check passed for `app.js`
- nested Git repo detection tested with a temporary repo layout where `PiServer` is a subfolder under a parent repo

## Expected validation on the Pi
1. Place PiServer under a real checkout like `/home/pi/PiDrive/PiServer`
2. Start the server
3. Open the web UI
4. Click **Check repo**
5. Confirm branch / commit / remote show correctly
6. Push a tiny change to GitHub
7. Click **Update from Repo**
8. Confirm the pull succeeds
9. Click **Restart service** if code changed

## Notes
This patch does **not** change docking, tabs, or other UI layout logic.
It is intentionally focused only on making repo-backed update work from the stable base build.
