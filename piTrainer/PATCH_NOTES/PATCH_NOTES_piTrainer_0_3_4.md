# PATCH NOTES — piTrainer_0_3_4

## Summary
Added a new **Preprocess** tab to the trainer so you can preview and apply dataset preprocessing recipes before training.

## Added
- New **Preprocess** tab in the main window.
- **Source Summary** panel for loaded rows, active training rows, sessions, and current train image size.
- **Preprocess Config** panel with:
  - source selection (loaded dataset or current filtered rows)
  - mode filter
  - steering range filter
  - speed range filter
  - image-size controls
- **Preprocess Actions** panel with:
  - preview recipe
  - apply to loaded data
  - reset to baseline loaded filter
  - sync image size to Train tab
- **Preprocess Preview** panel showing before/after counts and value ranges.
- **Preprocess Log** panel.

## Integration changes
- Added the new tab to the main tab bar.
- Added `Ctrl+4` shortcut for the Export tab after the new tab order became:
  - `Ctrl+1` Data
  - `Ctrl+2` Preprocess
  - `Ctrl+3` Train
  - `Ctrl+4` Export
- Data page now exposes `refresh_from_state()` so preprocessing changes can immediately refresh the Data tab preview.

## Behavior
- Preprocessing changes update the active `filtered_df` used for training.
- Original source files are not modified by this tab.
- Applying a preprocessing recipe resets prepared train/val splits and clears the current model/history to avoid stale state.

## Verification
- Python compile check passed on all patched files.
- Basic preprocessing service sanity-check passed with sample data.
