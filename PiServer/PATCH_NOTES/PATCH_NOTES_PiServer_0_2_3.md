# PATCH NOTES — PiServer_0_2_3

## Goal
Fix the startup/import failure after the 0_2_1/0_2_2 transition.

## What changed
- Restored a full working `PiServer/piserver/app.py` based on the 0_2_1 app module, with version bump to `0_2_3`.
- Simplified `PiServer/piserver/__init__.py` so importing the package no longer tries to import `create_app` during package initialisation.
- Reworked `PiServer/server.py` to load `piserver/app.py` directly and fail with a clear runtime error if `create_app()` is missing.

## Why
The previous startup path could still fail if the working tree had an older or partial `piserver/app.py`, or if package initialisation imported `piserver.app` at the wrong time.

## Files included
- `PiServer/piserver/app.py`
- `PiServer/piserver/__init__.py`
- `PiServer/server.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_3.md`

## Validation
Run:
```bash
cd ~/PiDrive/PiServer
python3 server.py
```
Expected: Flask starts without `ImportError: cannot import name 'create_app'`.
