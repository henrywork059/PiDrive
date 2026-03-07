# PATCH NOTES — piTrainer_0_3_0

## Promotion summary
This package promotes the reviewed piTrainer desktop app to **stable baseline version 0_3_0**.

## Review performed
- Reconstructed the current project from the working baseline plus patch deltas 0_2_6 through 0_2_10
- Removed cache artifacts and old nested packaging leftovers from the stable deliverable
- Ran Python compile checks across the assembled project
- Ran low-level sanity checks on the data filter and plotting services
- Manually reviewed the latest Data page wiring, dock-page layout flow, overlay controls, playback controls, and plot panel integration

## Stable features included
- PySide6 desktop GUI with dark theme
- Dockable panels on Data / Train / Export pages
- Main Data content as dock panels instead of a fixed center widget
- Session selection, frame filtering, delete selected frame
- Image overlay controls for speed and steering
- Playback control panel with play / stop / restart / speed
- Data plotting panel with multiple plot modes
- Training and export pages retained from the working baseline

## What was checked
- No syntax errors found during compile check
- No constructor/callback mismatch found in the reviewed current state
- Filter and plot service logic returned expected results on sample data

## Known review limits
- Full live GUI runtime was not executed in this environment because local desktop dependencies and interactive display behavior cannot be fully exercised here
- Final runtime still depends on the target PC environment having compatible PySide6 / TensorFlow / Matplotlib installs

## Packaging notes
- This stable zip is a **full baseline package**
- It excludes `__pycache__` and `.pyc` files
- Subsequent bug-fix updates can continue as patch-only zips if requested
