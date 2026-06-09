# PATCH NOTES — piTrainer_0_10_6 Non-Overwriting Model Artifact Saves

## Request summary

Make sure saved model files do not overwrite earlier saved models when the same default file name is used. Apply the same timestamped fallback approach used by trained `.keras` saves to exported model artifacts as well.

## Cause / root cause

The Train page already avoided overwriting `*_trained.keras` by adding a timestamp when the default trained-model path already existed. The Export page did not have the same protection: repeated exports with the default base name could reuse paths such as `picar_model.keras`, `picar_model.tflite`, or `picar_model_int8.tflite` and silently replace older exported files.

The trained `.keras` save path also only checked one timestamped fallback. If two saves happened within the same second and the timestamped file already existed, a collision was still possible.

## Files changed

- `piTrainer/piTrainer/services/export/export_service.py`
  - Adds `next_available_model_artifact_path(...)` to choose a non-overwriting artifact path.
  - Adds `overwrite_guard_notes(...)` so the UI/log can explain when a timestamped copy was used.
  - Updates `.keras` export to save to `base_name.keras` only when it is free; otherwise it saves to `base_name_YYYYMMDD_HHMMSS.keras`.
  - Updates `.tflite` export to save to `base_name.tflite` only when it is free; otherwise it saves to `base_name_YYYYMMDD_HHMMSS.tflite`.
  - Updates quantized `.tflite` export to save to `base_name_int8.tflite` only when it is free; otherwise it saves to `base_name_int8_YYYYMMDD_HHMMSS.tflite`.
  - Adds a counter fallback such as `_02` if multiple saves happen in the same second.
- `piTrainer/piTrainer/pages/train_page.py`
  - Uses the same shared non-overwriting path helper for trained `.keras` saves.
  - Shows a clear note in the Train save indicator when the default name already existed and a timestamped copy was used.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.10.6 / piTrainer_0_10_6`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_10_6.md`
  - Adds this patch note.

## Exact behavior changed

- Repeated Export actions no longer overwrite earlier default-named exported model files.
- Exporting with default `picar_model` now creates:
  - `picar_model.keras` if free;
  - `picar_model_YYYYMMDD_HHMMSS.keras` if `picar_model.keras` already exists;
  - `picar_model.tflite` if free;
  - `picar_model_YYYYMMDD_HHMMSS.tflite` if `picar_model.tflite` already exists;
  - `picar_model_int8.tflite` or `picar_model_int8_YYYYMMDD_HHMMSS.tflite` for quantized export.
- If the timestamped name also exists, piTrainer appends a counter such as `_02` instead of overwriting.
- The existing save/export indicators from `0.10.4` continue to show the exact final saved path.
- The Train page now uses the same collision-safe helper as Export, so trained `.keras` saves are protected even during very fast repeated saves.

## Behavior intentionally preserved

This patch does not change:

- model architecture;
- training configuration or batch size;
- validation calculations;
- TFLite output ordering from earlier patches;
- Data default sort from `0.10.4`;
- model save/export status labels from `0.10.4`;
- Session Source multi-selection preservation from `0.10.5`;
- manual Session Source drag-resize from `0.10.3`;
- the real entry point `piTrainer/main.py`.

## Compatibility / migration notes

- Existing saved models are not moved or renamed.
- Existing output folders keep working.
- Users can still choose the same base file name; piTrainer now protects older files by creating a timestamped new file when needed.
- The Export page and Train page still link the latest saved model/TFLite path into the next workflow step.

## Rollback-risk check

Checked the current `0.10.5` code state and recent piTrainer patch notes before finalizing:

- `PATCH_NOTES_piTrainer_0_10_5.md`
- `PATCH_NOTES_piTrainer_0_10_4.md`
- `PATCH_NOTES_piTrainer_0_10_3.md`
- `PATCH_NOTES_piTrainer_0_10_2.md`

Confirmed this patch builds forward from `0.10.5`. It does not roll back the `0.10.5` Session Source selection fix, does not remove the `0.10.4` Data default sort or save indicators, and does not remove the `0.10.3` manual Session Source resize handle.

## Verification actually performed

- Started from the latest available `0.10.5` patch-applied state.
- Inspected the Train save path and Export artifact path generation.
- Confirmed the real entry point remains `piTrainer/main.py`.
- Ran Python syntax compilation from the component root:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under the component with `ast.parse` successfully.
- Ran a direct helper check confirming existing default files produce timestamped non-overwriting paths for `.keras`, `.tflite`, and `_int8.tflite` names.
- Verified the updated version file reports `0.10.6 / piTrainer_0_10_6`.
- Verified the patch zip contains only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI clicking was not run in this Linux sandbox because PySide6 is not installed here.
- Real TensorFlow training/export was not run in this sandbox.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- Timestamped names use local system time at save/export time. If exact run metadata is needed later, a future patch could add a small sidecar export manifest listing model source, dataset, training settings, and artifact paths.
