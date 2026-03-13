# PATCH NOTES — PiServer_0_2_4

## Goal
Repair the PiServer startup/import path after the repo ended up with a mixed set
of startup files and service files.

## Problem observed
Running `python3 server.py` failed with:

- `ImportError: cannot import name 'MotorService' from 'piserver.services.motor_service'`

This indicated the Pi had a mismatched `motor_service.py` and an eager
`piserver/services/__init__.py` that imported all services during package load.

## Changes
- Replaced `PiServer/piserver/services/motor_service.py` with a complete,
  known-good version that defines `MotorService`.
- Simplified `PiServer/piserver/services/__init__.py` so importing one service
  module does not trigger eager imports of the whole services package.

## Expected result
- `python3 server.py` should start again.
- Manual drive and motor tuning code paths have the required `MotorService`
  methods available.

## Apply
Overwrite the files from this patch zip into your PiServer folder, then run:

```bash
cd ~/PiDrive/PiServer
python3 server.py
```
