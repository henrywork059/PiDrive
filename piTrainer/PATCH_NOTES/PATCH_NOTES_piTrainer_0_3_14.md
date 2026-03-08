# PATCH NOTES — piTrainer_0_3_14

## Summary
Small overlay patch to improve the path preview readability.

## What was wrong
- The path corridor was not curving strongly enough, so it could read like a slightly bent straight line.
- The displayed path direction felt inverted in use.

## What changed
- Reworked the path geometry to use a stronger lateral bend.
- Restored the path direction so the preview curve follows the expected screen-side direction again.
- Increased the visible corridor width.
- Added a light corridor fill so the path is easier to read at a glance.
- Removed the extra endpoint reference line that made the overlay feel more like a vector than a path.

## Files changed
- `piTrainer/services/data/overlay_service.py`

## Verification
- Python syntax compile check passed for the patched file.
- Packaged as patch-only zip with the same wrapper-folder style and no cache files.
