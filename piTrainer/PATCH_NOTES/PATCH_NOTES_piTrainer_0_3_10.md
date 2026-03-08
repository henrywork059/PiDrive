# PATCH NOTES — piTrainer_0_3_10

## Summary
This patch adds a more intuitive **Path Preview** overlay for the Image Preview panel and keeps the existing **Drive Arrow** as an optional debug overlay.

## What changed
- Added a new **Show path preview** overlay option.
- Path Preview draws a short curved trajectory from the middle-bottom of the frame.
- Path length is influenced by speed.
- Curve direction and bend are influenced by steering.
- Kept the existing **Drive Arrow** overlay as a separate optional checkbox.
- Updated overlay help text to explain the difference between Path Preview and Drive Arrow.
- Path Preview is enabled by default in the overlay options and image preview fallback state.

## Changed files
- `piTrainer/services/data/overlay_service.py`
- `piTrainer/panels/data/overlay_control_panel.py`
- `piTrainer/panels/data/image_preview_panel.py`

## Notes
- This patch changes visualization only.
- It does not change training labels, editing logic, or saved dataset values.

## Verification
- Python compile check passed on the patched files.
- Checked that the new overlay option is passed through to the image preview panel.
