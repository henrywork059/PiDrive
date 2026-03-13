# PATCH NOTES — PiServer_0_2_2

## Purpose
Fix the startup import failure introduced after `0_2_1`, where running `python3 server.py` could fail with:

`ImportError: cannot import name 'create_app' from 'piserver.app'`

## Root cause
`server.py` imported `create_app` from `piserver.app`, while `piserver/__init__.py` also eagerly imported `create_app` from `.app` during package initialisation. On some Pi environments this could trip an import-time package initialisation issue and leave `piserver.app` visible before `create_app` had been exported cleanly.

## Changes
- Changed `PiServer/piserver/__init__.py` to export `create_app` lazily.
- Changed `PiServer/server.py` to import `create_app` from `piserver` instead of directly from `piserver.app`.

## Expected result
`python3 server.py` should start normally again from the PiServer folder.

## Files in this patch
- `PiServer/piserver/__init__.py`
- `PiServer/server.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_2.md`
