# PATCH NOTES — piTrainer_0_2_2

## Summary
Added dockable page workspaces and keyboard shortcuts to the PySide6 trainer.

## Cause
The previous desktop layout used fixed panel placement, so panels could not be moved from their default positions.

## Changes
- Converted Data, Train, and Export pages into dockable workspaces.
- Each panel can now be dragged, re-docked, tabbed with other panels, or floated.
- Added layout persistence with QSettings.
- Added reset-layout shortcut: Ctrl+Shift+R.
- Added navigation and action shortcuts, with F1 help dialog.
- Updated README with the new workflow.

## Verification
- Python compile check for the full project passed.
- Packaging check confirmed the project folder and patch notes are inside the zip.

## Future improvements
- Add a View menu with panel visibility toggles.
- Add export/import for saved workspace layouts.
- Add user-editable shortcut customization.
