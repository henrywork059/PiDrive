# PATCH NOTES — piTrainer_0_11_0 V11 Stable Baseline Promotion

## Request summary

Promote the accepted current piTrainer state to V11 and provide a patch-only V11 package. The user confirmed the latest non-overwriting model save patch is good and asked for V11 with patch-only delivery.

## Cause / root cause

The V10 patch line has accumulated accepted fixes through `piTrainer_0_10_6`, including Validation frame-review navigation, Session Source resizing and selection preservation, Data default sorting by session date/time then frame id, clearer model save indicators, and non-overwriting default model artifact saves. A V11 stable promotion gives the next work a clean `0_11_x` forward patch line.

## Files changed

- `piTrainer/piTrainer/version.py`
  - Updates visible app version from `0.10.6` to `0.11.0`.
  - Updates patch/version string from `piTrainer_0_10_6` to `piTrainer_0_11_0`.
- `piTrainer/AGENTS.md`
  - Updates baseline guidance from V10 to V11.
  - Updates future patch-only naming guidance to `piTrainer_0_11_x_patch.zip`.
  - Preserves anti-rollback guidance for accepted V7/V8/V9/V10 behaviours.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Updates the stable baseline note and version-gate manifest example for V11.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_0.md`
  - Adds this patch note.

## Exact behavior changed

- The app now reports:
  - `APP_VERSION = 0.11.0`
  - `PATCH_VERSION = piTrainer_0_11_0`
  - status text `Version 0.11.0 (piTrainer_0_11_0)`
- Future piTrainer patch guidance now points to the `0_11_x` line.
- No runtime workflow logic was intentionally changed in this promotion patch.

## Behavior intentionally preserved

This patch preserves accepted V10 behaviour through `0.10.6`, including:

- Validation and TFLite Check frame-review table behaviour, edit-return selection memory, and edited-row highlighting;
- manual Session Source drag-resize handle;
- Data default sort by session date/time first, then frame id inside the session;
- clear save/export path indicators;
- Session Source multi-selection preservation when editing validation frames in Data;
- non-overwriting save/export naming for `.keras`, `.tflite`, and quantized `.tflite` model artifacts;
- existing training, validation, export, preprocessing, Data editing, hide/recover, and overlay behaviours;
- the real entry point `piTrainer/main.py`.

## Compatibility / migration notes

- No dataset files, labels, recordings, models, or config files are migrated or rewritten by this patch.
- The online version-gate manifest is not bundled from GitHub in this patch. Before distributing a controlled V11-only release with the gate enabled, update the online manifest to allow or require `0.11.0`, or rely on the existing `minimum_version` logic if the manifest is already configured to allow newer versions.

## Rollback-risk check

Checked the current `0.10.6` code state and recent piTrainer patch notes before finalizing:

- `PATCH_NOTES_piTrainer_0_10_6.md`
- `PATCH_NOTES_piTrainer_0_10_5.md`
- `PATCH_NOTES_piTrainer_0_10_4.md`
- `PATCH_NOTES_piTrainer_0_10_3.md`

Confirmed this promotion builds forward from `0.10.6`. It does not roll back the `0.10.6` non-overwriting model artifact save behaviour, the `0.10.5` Session Source selection fix, the `0.10.4` Data default sort/save indicators, or the `0.10.3` manual Session Source resize handle.

## Verification actually performed

- Started from the latest available `0.10.6` patch-applied state.
- Confirmed the real entry point remains `piTrainer/main.py`.
- Ran Python syntax compilation from the component root:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under the component with `ast.parse` successfully.
- Verified the updated version file reports `0.11.0 / piTrainer_0_11_0`.
- Verified the patch zip contains only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI clicking was not run in this Linux sandbox because PySide6 is not installed here.
- Real TensorFlow training/export was not run because this promotion patch does not change model training/export logic.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- Future bug-fix patches should continue as `piTrainer_0_11_1_patch.zip`, `piTrainer_0_11_2_patch.zip`, and so on unless a newer stable baseline is promoted.
