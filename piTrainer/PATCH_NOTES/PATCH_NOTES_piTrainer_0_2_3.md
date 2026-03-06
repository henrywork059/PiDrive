# PATCH NOTES — piTrainer_0_2_3

## Summary

This patch cleans up the dockable UI by removing the wasted default middle area, making the drag bars much clearer, improving checkbox visibility, and splitting the preview into separate record-table and image-preview panels.

## Why this patch was made

The previous dockable layout technically allowed panel movement, but the default workspace still showed a useless middle area with a drag message, the dock title bars were too subtle in dark mode, and the checkbox styling was not clear enough. The combined preview panel also made it harder to reposition the image preview independently.

## Final changes

### 1) Removed the wasted middle area
- The Data page now uses the record-preview table as the main center workspace.
- The Train page now uses the training-history chart as the main center workspace.
- The Export page now uses the export log as the main center workspace.
- This removes the empty “drag panel...” area from the normal default layout.

### 2) Made drag bars more obvious
- Updated dock title bars to a brighter blue with stronger contrast.
- Styled dock separators so resize / drag boundaries are easier to see.

### 3) Made checkboxes clearer
- Added a stronger checkbox border and a brighter checked fill state.
- Increased indicator size for easier visibility in dark mode.

### 4) Split preview into separate panels
- The record table remains its own panel/workspace.
- The image preview is now a dedicated separate panel.
- This makes image preview placement independent from the table panel.

## Files changed
- `piTrainer/pages/dock_page.py`
- `piTrainer/pages/data_page.py`
- `piTrainer/pages/train_page.py`
- `piTrainer/pages/export_page.py`
- `piTrainer/panels/data/preview_panel.py`
- `piTrainer/panels/data/image_preview_panel.py`
- `piTrainer/main_window.py`
- `piTrainer/ui/styles.py`
- `README.md`

## Verification
- Python compile check completed successfully after the patch.
- The packaged zip includes the updated code and patch notes.
