# PATCH NOTES — piTrainer_0_9_16 Data Overlay Defaults, Text Weight, and Naming Cleanup

## Request summary

Patch the v9 Data page overlay so that:

- Overlay text is about 30% thicker.
- Speed bar and steering arc are visible by default.
- The middle road-guide label is hidden when the speed bar or steering arc is visible.
- Overlay text is shorter and more accurate.
- Overlay text positions are reviewed to avoid overlapping the default controls.
- User-facing naming is unified around `Steering` and `Speed` instead of mixed `steer`, `STR`, `SPD`, or `throttle` wording.

## Cause / root cause

The `0.9.15` overlay style changed Data page curve colour and text size, but several older overlay labels remained abbreviated (`SPD`, `STR`, `STR ARC`) and the speed/steering gauge overlays were still disabled by default.

The road-guide label was also drawn near the middle/bottom of the preview. With the speed bar and steering arc enabled, that label could clutter the preview and compete with the dedicated gauge labels.

Some review panels still used mixed wording such as `Steer Diff`, `Pred Steer`, and `Steer/Speed`, while the rest of the app had moved toward `Steering` and `Speed`.

## Files changed

- `piTrainer/piTrainer/services/data/overlay_primitives.py`
  - Adds a 30% overlay text weight increase.
  - Updates speed/steering gauge labels from abbreviated text to `Speed` and `Steering`.
  - Moves and widens overlay label rectangles so the thicker/larger text has more room.
  - Updates legacy debug path text to use `Speed` and `Steering`.
- `piTrainer/piTrainer/services/data/overlay_road.py`
  - Adds a `show_label` option for the road-guide text label.
  - Shortens road label wording and replaces `trapezium`/`road curve` wording with `Straight`/`Curve`.
  - Slightly moves and widens the road label position for readability when it is shown.
- `piTrainer/piTrainer/services/data/overlay_service.py`
  - Draws path overlays before gauge overlays so speed bar and steering arc stay visible on top.
  - Hides the middle road-guide label whenever speed bar or steering arc is enabled.
  - Applies the same thicker text style to Data page deploy comparison legend text.
  - Shortens deploy legend text to `Target path` and `AI path`.
- `piTrainer/piTrainer/panels/data/overlay_control_panel.py`
  - Makes `Speed bar` and `Steering arc` checked by default.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Makes speed bar and steering arc visible in the preview defaults.
  - Shortens overlay metadata text.
  - Makes deployed-output metadata use `AI Steering/Speed` wording.
- `piTrainer/piTrainer/panels/data/model_deploy_panel.py`
  - Renames `Sort Steer Diff` to `Sort Steering Diff`.
- `piTrainer/piTrainer/panels/data/preview_model.py`
  - Renames the table header `Steer Diff` to `Steering Diff`.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Uses title-case `Steering` and `Speed` in the current-row summary.
- `piTrainer/piTrainer/panels/train/train_epoch_review_panel.py`
  - Updates review text to `Target Steering/Speed` and `AI Steering/Speed`.
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
  - Updates table headers and metadata text to `True Steering`, `AI Steering`, `AI Speed`, and `AI Steering/Speed`.
- `piTrainer/piTrainer/services/export/export_service.py`
  - Updates the user-facing export note to `[steering, speed]`.
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
  - Updates the user-facing horizontal-flip note to say Speed is preserved.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.16 / piTrainer_0_9_16`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_16.md`
  - Adds this patch note.

## Exact behavior changed

- Data page speed bar is visible by default.
- Data page steering arc is visible by default.
- Data page middle road-guide text is hidden by default because the speed bar and steering arc are enabled.
- If the user disables both the speed bar and steering arc, the middle road-guide label can still appear with shorter `Speed`, `Steering`, and `Straight/Curve` text.
- Overlay text is still 30% larger from `0.9.15` and is now also about 30% thicker through the overlay font weight.
- Data page gauge labels use clearer text:
  - `Speed 0.00`
  - `Steering 0.00`
- Gauge labels are moved/widened so the larger and thicker text has more room.
- Path/road overlays are drawn before the speed/steering gauge overlays, so the gauges remain visible on top.
- User-facing Data/Deploy/Train/Validate wording is more consistent around `Steering` and `Speed`.

## Behavior intentionally preserved

This patch does not change:

- Data Workflow tab order: `1 Load`, `2 Hide & Recover`, `3 Filter`, `4 Review`, `5 Deploy`.
- Session working-folder sync from `0.9.14`.
- Top bar removal from `0.9.14`.
- Data page green curve colour and red enlarged overlay text from `0.9.15`.
- Validate and TFLite Check defaulting to all visible rows from `0.9.15`.
- Deploy output columns, diff sorting, overlay preview, or Apply AI to Selected.
- Up/Down next-frame navigation fixes.
- Preprocess done banner and default source/mode behavior.
- Hide/Recover and hidden permanent-delete behavior.
- The `0.9.11` Data page mixin split.
- The `0.9.12` Preview/Overlay refactor.
- The `0.9.13` Validation service refactor.

## Rollback-risk check

Checked the latest current code state and the previous v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_15.md`
- `PATCH_NOTES_piTrainer_0_9_14.md`
- `PATCH_NOTES_piTrainer_0_9_13.md`

Confirmed this patch builds forward from `0.9.15`. It does not replace the refactored overlay modules, Data page, Preview panel, Validation service, session working-folder changes, top-bar removal, or validation visible-row defaults with older files.

## Verification actually performed

- Applied all v9 patches from `0.9.0` through `0.9.15` before patching.
- Inspected the real overlay path:
  - `image_preview_panel.py`
  - `overlay_control_panel.py`
  - `overlay_service.py`
  - `overlay_road.py`
  - `overlay_primitives.py`
- Inspected user-facing naming in Data table, Deploy, Train review, Validation review, Preprocess notes, and Export notes.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Compared against the `0.9.15` reconstructed baseline and confirmed the patch only changes the intended Python files plus this patch note.
- Verified the version file reports `0.9.16 / piTrainer_0_9_16`.
- Prepared a patch-only zip with only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI startup/clicking was not run in this Linux sandbox because PySide6 is not installed here.
- Real frame overlay rendering was not visually checked in this sandbox.
- Real model validation/TFLite check was not run for this overlay/text patch.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- Internal model/output column names still use `throttle` where required for compatibility with existing labels, training code, and saved model outputs. This patch changes user-facing wording only, so existing datasets and models remain compatible.
- The Overlay panel `Clear` button still clears all overlay checkboxes. Re-opening the app/default panel state starts with the speed bar and steering arc enabled.
