# PATCH NOTES — piTrainer_0_2_5

## Issue fixed
The app could fail immediately on startup with:

`TypeError: DataControlPanel.__init__() got an unexpected keyword argument 'autoplay_callback'`

## Root cause
Patch `0_2_4` updated `data_page.py` to pass a new `autoplay_callback` argument into `DataControlPanel`, but `data_control_panel.py` still used the older constructor signature.

There was also a second integration mismatch: `data_page.py` expected the preview panel to provide autoplay and selected-record helper methods, but `preview_panel.py` did not yet implement them.

## Changes made
- Updated `piTrainer/panels/data/data_control_panel.py`
  - Added optional `autoplay_callback`
  - Added an **Auto Play Frames** button
  - Added `set_autoplay_active()` so the button text updates correctly
- Updated `piTrainer/panels/data/preview_panel.py`
  - Added `QTimer` based frame autoplay
  - Added `toggle_autoplay()`
  - Added `stop_autoplay()`
  - Added `selected_record()`
  - Added `current_row()` helper
  - Made preview table read-only and kept row selection behavior stable
  - Reset DataFrame index on load so table row selection matches the preview records reliably

## Verification
- Ran `python -m compileall main.py piTrainer`
- Verified the previously failing constructor mismatch is removed in the patched source
- Verified the preview panel now provides the methods used by `data_page.py`

## Notes
This patch is focused on restoring app startup and making the new autoplay/delete wiring consistent with the Data page.
