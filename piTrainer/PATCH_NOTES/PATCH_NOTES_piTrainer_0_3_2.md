# PATCH NOTES — piTrainer_0_3_2

## Summary
This patch combines the old Record Root and Session panels into a single Session Source panel, saves the last used records root, and upgrades the Image Preview into an interactive frame editor.

## Changes
- Replaced separate Record Root + Sessions panels with one `Session Source` panel.
- Added persistent save/restore of the last used records root via `QSettings`.
- Added editable steering and speed sliders under Image Preview.
- Added click-and-drag editing directly on the preview image.
- Added a new overlay option: drive arrow.
- Added frame edit persistence back into `records.jsonl`.
- Improved preview selection persistence after edits.

## Notes
- Speed editing is mapped to `throttle` in the record data.
- Steering is clipped to `[-1.0, 1.0]`.
- Speed is clipped to `[0.0, 1.0]` to match the current trainer overlay logic.
- Frame edits are written back to the matching JSONL row using session + frame id + timestamp + image filename matching.

## Files changed in this patch
- `piTrainer/pages/data_page.py`
- `piTrainer/panels/data/session_source_panel.py`
- `piTrainer/panels/data/overlay_control_panel.py`
- `piTrainer/panels/data/preview_panel.py`
- `piTrainer/panels/data/image_preview_panel.py`
- `piTrainer/services/data/overlay_service.py`
- `piTrainer/services/data/edit_service.py`
- `PATCH_NOTES/PATCH_NOTES_piTrainer_0_3_2.md`
