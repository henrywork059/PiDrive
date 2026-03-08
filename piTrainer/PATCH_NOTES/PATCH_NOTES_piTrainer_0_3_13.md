# PATCH NOTES — piTrainer_0_3_13

## Summary
This patch improves the model-review and frame-edit workflow between Validation and Data, makes the path preview easier to understand for label editing, adds bad-prediction filtering in Validation, and performs a small maintenance pass on the training/config and overlay code.

## Main changes
- Added **Edit in Data** handoff from Validation frame review back to the raw Data editor.
- Added **bad prediction filtering** in Validation with:
  - Show only bad predictions
  - Error threshold
  - Worst / original / best ordering
  - Quick Best / Worst buttons
- Improved **Path Preview** so it now behaves more like a short driving corridor/path and matches the click-edit endpoint logic more closely.
- Refactored the overlay/path code into clearer shared helpers for easier maintenance.
- Enriched validation frame rows with mode, timestamp and image path metadata for better browsing and editing handoff.

## Added training-help options
- Added **Gradient clipnorm** option to training config.
- Added **L2 regularization** option to training config.
- Added **Epoch review sample count** option to training config.
- Updated model build/compile flow so these options are actually used.

## Changed files
- `piTrainer/app_state.py`
- `piTrainer/main_window.py`
- `piTrainer/pages/data_page.py`
- `piTrainer/pages/validation_page.py`
- `piTrainer/panels/train/train_config_panel.py`
- `piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/services/data/overlay_service.py`
- `piTrainer/services/train/model_service.py`
- `piTrainer/services/train/worker.py`
- `piTrainer/services/validation/validation_service.py`

## Verification
- Python compile check passed on all patched files.
- Validation row building and filtering were sanity-checked with sample data.
- Overlay/path helper logic was sanity-checked with representative steering/speed values.
- Training config wiring was checked for constructor/callback consistency.

## Notes
- This is still a patch-only zip and keeps the same wrapper-folder and relative project paths as before.
- The new path preview now uses the same endpoint geometry as click-edit, so clicking near the visible path endpoint should feel more consistent than before.
