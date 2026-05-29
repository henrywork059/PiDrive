# piTrainer 0.8.7 Patch Notes

## Request summary

Make the `Save Trained Model` button in the Train page visually green/filled so it is easier to recognise as an important action after training.

## Cause / reason

The `Save Trained Model` button added in `0.8.6` used the secondary button role. That made it look like a low-priority grey action even though it is the main action for saving the trained `.keras` model after a training run.

## Files changed

- `piTrainer/piTrainer/panels/train/train_control_panel.py`
- `piTrainer/piTrainer/version.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_7.md`

## Exact behavior changed

- Changed `Save Trained Model` from the secondary button style to the central green primary button style.
- Kept the existing `0.8.6` save-folder selector and remembered-directory behavior unchanged.
- Kept the button wiring to the existing trained-model save callback unchanged.
- Updated the displayed app version to `0.8.7 / piTrainer_0_8_7`.

## Compatibility / rollback safety

- This is a UI styling-only patch.
- No training logic, save-path logic, validation logic, export logic, or TFLite output logic was changed.
- The patch builds forward from `0.8.6` and preserves the previous `0.8.1` through `0.8.6` accepted changes.

## Verification performed

- Applied on top of the reconstructed `0.8.6` state.
- Ran `python3 -m compileall -q main.py piTrainer` successfully.
- Ran an AST parse check over all Python files successfully.
- Verified the changed button role is now `primary` in `train_control_panel.py`.
- Verified patch package contains only the changed files and this patch note.

## Known limits / next steps

- The live PySide6 GUI was not opened in this sandbox because PySide6 is not installed here.
