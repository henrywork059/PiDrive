# PATCH NOTES — PiServer_0_2_12

## Summary
Hotfix patch to recover a broken PiServer startup where `python3 server.py` fails with:

`ImportError: cannot import name 'create_app' from 'piserver.app'`

## Root cause
On the Pi, `PiServer/piserver/app.py` was most likely partially overwritten or left in an inconsistent state during patch copy or merge cleanup. The intended project code still defines `create_app()`, but the file present on the Pi did not expose it at runtime.

## Changes in this patch
- Re-shipped a known-good `PiServer/piserver/app.py`
- Bumped app version to `0_2_12`
- Re-shipped `PiServer/server.py`
- Hardened `PiServer/piserver/__init__.py` so missing factory errors are clearer and easier to diagnose

## Files included
- `PiServer/piserver/app.py`
- `PiServer/piserver/__init__.py`
- `PiServer/server.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_12.md`

## Install
Copy these files over your existing `PiServer` folder, preserving paths.

## Verify
Run:

```bash
cd ~/PiDrive/PiServer
python3 -m py_compile piserver/app.py piserver/__init__.py server.py
python3 server.py
```

Expected result: PiServer starts without the `create_app` import error.
