# PATCH NOTES — piTrainer_0_3_3

## Summary
This patch fixes two steering overlay presentation issues on the Image Preview.

## Changes
- Updated the steering horizontal bar so the fill clearly starts from the center zero marker.
- Split steering fill colors by direction for clearer left/right reading.
- Fixed the steering semi-circle overlay so it grows from the center zero position without the doubled-color look.
- Kept the patch limited to the overlay drawing service only.

## Notes
- Negative steering now uses the warm steering color.
- Positive steering now uses the cool steering color.
- The semi-circle overlay now uses a center-origin quarter-span per side, so zero stays at the middle top of the arc.

## Files changed in this patch
- `piTrainer/services/data/overlay_service.py`
- `PATCH_NOTES/PATCH_NOTES_piTrainer_0_3_3.md`
