# PATCH NOTES — piTrainer_0_9_15 Data Overlay Colour and Validation Dataset Defaults

## Request summary

Patch the v9 app so that:

- Data page frame overlays use green curve/path lines.
- Data page overlay text uses red text.
- Data page overlay text is about 30% larger.
- Validation dataset default is all visible rows.

## Cause / root cause

The Data page overlay styling still used the older cyan road-guide curve and mostly white overlay text. That made the path guide less consistent with the user's desired visual language and made overlay labels harder to read.

The Validate and TFLite Check dataset selectors also still defaulted to the saved validation split. For the current workflow, the more useful default is the visible table rows selected/filtered in Data, because the user is usually reviewing the active visible dataset before validating or checking export output.

## Files changed

- `piTrainer/piTrainer/services/data/overlay_primitives.py`
  - Adds shared Data overlay text colour and text-scale constants.
  - Enlarges overlay labels by 30% by default.
  - Makes default overlay labels red.
- `piTrainer/piTrainer/services/data/overlay_road.py`
  - Changes the Data page PiSD road-guide curve colour from cyan to green.
  - Sends the PiSD road-guide text label through the red enlarged Data overlay label style.
  - Expands the road-guide text rectangle so the larger label has more room.
- `piTrainer/piTrainer/services/data/overlay_service.py`
  - Adds optional legend text colour and text-scale arguments for prediction comparison overlays.
  - Keeps existing callers compatible by defaulting to the old white, normal-sized legend text unless a caller opts in.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Applies the red, 30%-larger legend text style to Data page deployed-output comparison overlays.
- `piTrainer/piTrainer/panels/validation/validation_config_panel.py`
  - Changes the default validation dataset selector to `All visible rows`.
- `piTrainer/piTrainer/panels/export_validation/export_validation_config_panel.py`
  - Changes the default TFLite Check dataset selector to `All visible rows` for consistency with Validate.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.15 / piTrainer_0_9_15`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_15.md`
  - Adds this patch note.

## Exact behavior changed

- Data page road-guide/path overlay curves now draw in green.
- Data page overlay text labels now draw in red.
- Data page overlay text labels are scaled to 130% of the painter font size.
- Data page deployed-output comparison legend text also uses the red 130% text style.
- Validate now opens with `All visible rows` selected as the dataset.
- TFLite Check now opens with `All visible rows` selected as the dataset.
- The existing dataset routing remains compatible:
  - `All visible rows` uses the currently visible/filtered Data rows.
  - `Validation split` uses the validation split.
  - `Training split` uses the training split.

## Behavior intentionally preserved

This patch does not change:

- Data Workflow tab order: `1 Load`, `2 Hide & Recover`, `3 Filter`, `4 Review`, `5 Deploy`.
- Session working-folder sync from `0.9.14`.
- Top bar removal from `0.9.14`.
- Deploy output columns, diff sorting, overlay preview, or Apply AI to Selected.
- Up/Down next-frame navigation fixes.
- Preprocess done banner and default source/mode behavior.
- Hide/Recover and hidden permanent-delete behavior.
- The `0.9.11` Data page mixin split.
- The `0.9.12` Preview/Overlay refactor.
- The `0.9.13` Validation service refactor.

## Rollback-risk check

Checked the latest current code state and the previous v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_14.md`
- `PATCH_NOTES_piTrainer_0_9_13.md`
- `PATCH_NOTES_piTrainer_0_9_12.md`

Confirmed this patch builds forward from `0.9.14`. It does not replace the refactored Data page, Preview panel, Overlay service, Validation service, or session working-folder changes with older files.

## Verification actually performed

- Applied all v9 patches from `0.9.0` through `0.9.14` before patching.
- Inspected the real Data page preview overlay path:
  - `image_preview_panel.py`
  - `overlay_service.py`
  - `overlay_road.py`
  - `overlay_primitives.py`
- Inspected the real Validate and TFLite Check dataset selector panels.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the version file reports `0.9.15 / piTrainer_0_9_15`.
- Prepared a patch-only zip with only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI startup/clicking was not run in this Linux sandbox because PySide6 is not installed here.
- Real frame overlay rendering was not visually checked in this sandbox.
- Real model validation/TFLite check was not run for this UI-default patch.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- Data page deployed-output comparison still uses green for the target curve and orange for the predicted curve so users can distinguish target labels from AI output. The legend text is red and larger on the Data page.
- Validate and TFLite Check both default to visible rows. Users can still manually choose the validation split or training split when needed.
