# PATCH NOTES — PiServer 0_1_6

## Goal
Make the web **Update from Git** button work correctly with the real GitHub repo layout (`PiDrive/PiServer`) while keeping the package cumulative with the earlier requested UI changes.

## Main changes
- Updated the Git update logic so PiServer no longer assumes `.git` is inside the `PiServer/` folder.
- Added proper detection for when PiServer is running inside a parent Git checkout such as:
  - `/home/pi/PiDrive/PiServer`
- Web Git status now reports the tracked project path inside the repo.
- The update action now gives a clearer error when PiServer is running from a standalone unzip instead of a Git clone.
- Updated the included `systemd` service file to the Git-backed no-venv layout:
  - `WorkingDirectory=/home/pi/PiDrive/PiServer`
  - `ExecStart=/usr/bin/python3 /home/pi/PiDrive/PiServer/server.py`
- Updated README instructions for:
  - no-venv startup
  - sparse Git clone of the `PiDrive` repo
  - using the web Update button safely

## Cumulative scope
This `0_1_6` package is intended as a cumulative patch bundle and includes the requested changes from:
- `0_1_1`
- `0_1_2`
- `0_1_3`
- `0_1_4`
- `0_1_5`
- plus the new `0_1_6` Git-backed update changes

## Safety
Update / restart remains blocked unless:
- recording is off
- throttle is zero
- emergency stop is enabled
