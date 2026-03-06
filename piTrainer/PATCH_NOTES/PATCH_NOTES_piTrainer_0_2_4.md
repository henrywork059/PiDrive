# PATCH NOTES — piTrainer_0_2_4

## Summary
This patch improves the Data page workflow for reviewing and curating recorded frames.

## Changes made
- Brightened the session panel checkbox indicator colors for better visibility in dark mode.
- Added a visible **Show Shortcuts** button in the UI toolbar and a second one in the Data Control panel.
- Added a **Delete Selected Frame** action that removes the selected row from `records.jsonl` and deletes the matching image file.
- Added **Auto Play Frames** on the Data page so the selected preview row advances automatically.
- Added a dedicated **Frame Filter** panel so the preview table can be filtered by text and by mode before selecting frames.
- Added shortcut support for the new actions:
  - `Delete` = delete selected frame
  - `Space` = start/stop autoplay

## File structure changes
- New panel: `piTrainer/panels/data/data_control_panel.py`
- New panel: `piTrainer/panels/data/frame_filter_panel.py`
- New service: `piTrainer/services/data/delete_service.py`
- New service: `piTrainer/services/data/filter_service.py`
- Updated: `piTrainer/pages/data_page.py`
- Updated: `piTrainer/panels/data/preview_panel.py`
- Updated: `piTrainer/panels/data/session_list_panel.py`
- Updated: `piTrainer/main_window.py`
- Updated: `piTrainer/ui/styles.py`
- Updated: `README.md`

## Verification
- Python syntax checked with `compileall`.
- Verified that the new modules import cleanly in the packaged project.

## Notes / known limits
- Frame deletion is matched by `session + frame_id + timestamp + image filename`. If older data has duplicate IDs and timestamps within one session, deletion will remove the first matching row.
- The preview table still shows the first 50 filtered rows for quick review.
