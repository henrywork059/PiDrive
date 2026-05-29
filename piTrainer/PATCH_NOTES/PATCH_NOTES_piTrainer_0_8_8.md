# piTrainer 0.8.8 Patch Notes

## Request summary

After running piTrainer, TensorFlow/TFLite printed noisy console messages such as:

- `WARNING: All log messages before absl::InitializeLog() is called are written to STDERR`
- `Ignored output_format`
- `Ignored drop_control_dependency`
- `MLIR V1 optimization pass is not enabled`
- `Warning: Please use the LiteRT interpreter from the ai_edge_litert package`
- `INFO: Created TensorFlow Lite XNNPACK delegate for CPU`

The app still ran, but these messages made the command window look like an error occurred.

## Cause / reason

These messages come from TensorFlow/TFLite internals during TFLite export and Export Validation interpreter creation/allocation.

The previous `0.8.5` export patch already captured normal Python `stdout`/`stderr`, but some TensorFlow Lite and absl messages are written directly to the process-level stdout/stderr file descriptors by native code. Python-level `redirect_stderr()` does not catch those low-level writes.

The LiteRT migration warning is also a Python warning raised by TensorFlow's bundled Lite interpreter. It is informational and does not mean the current TensorFlow Lite validation path failed.

## Files changed

- `piTrainer/piTrainer/utils/tf_log_utils.py`
- `piTrainer/piTrainer/services/export/export_service.py`
- `piTrainer/piTrainer/services/validation/validation_service.py`
- `piTrainer/piTrainer/version.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_8.md`

## Exact behavior changed

- Added a shared TensorFlow/TFLite log-suppression helper that captures:
  - Python `stdout`;
  - Python `stderr`;
  - Python warnings;
  - native stdout/stderr file descriptor writes from TensorFlow/TFLite/absl.
- TFLite export now also suppresses TensorFlow import-time and converter-time console noise.
- Export Validation now suppresses TensorFlow Lite interpreter creation and tensor-allocation console noise.
- The LiteRT migration warning is hidden during the current TensorFlow Lite interpreter path.
- Known useful summaries still appear in piTrainer's export notes/logs where applicable, instead of dumping raw TensorFlow diagnostics to the terminal.
- Updated the displayed app version to `0.8.8 / piTrainer_0_8_8`.

## Behavior intentionally not changed

- No training logic was changed.
- No saved-model path behavior was changed.
- No Export Validation prediction logic was changed.
- No TFLite output order or model conversion behavior was changed beyond suppressing console noise.
- The `0.8.7` green `Save Trained Model` button is preserved.
- The `0.8.6` Training-tab save-folder browser is preserved.
- The `0.8.5` ordered TFLite output export remains preserved.
- The `0.8.4` Data-page loaded-row validation behavior remains preserved.

## Compatibility / rollback safety

- This is a console-noise cleanup patch only.
- It builds forward from the accepted `0.8.7` state and does not roll back the earlier v8 fixes.
- If TensorFlow/TFLite raises a real Python exception, the app still surfaces the error through the existing validation/export error paths.
- The suppression context is only used around short TensorFlow/TFLite operations, not around the whole app.

## Verification performed

- Reconstructed the current state from:
  - `piTrainer_0_8_0.zip`
  - `piTrainer_0_8_1_patch.zip`
  - `piTrainer_0_8_2_patch.zip`
  - `piTrainer_0_8_3_patch.zip`
  - `piTrainer_0_8_4_patch.zip`
  - `piTrainer_0_8_5_patch.zip`
  - `piTrainer_0_8_6_patch.zip`
  - `piTrainer_0_8_7_patch.zip`
- Checked the latest and previous three relevant patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_8_7.md`
  - `PATCH_NOTES_piTrainer_0_8_6.md`
  - `PATCH_NOTES_piTrainer_0_8_5.md`
  - `PATCH_NOTES_piTrainer_0_8_4.md`
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a direct helper test confirming the new suppression helper captures:
  - normal Python stdout;
  - normal Python stderr;
  - native `os.write(2, ...)` stderr-style output.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed

- Live Windows/PySide6 GUI clicking was not run in this sandbox.
- Real TensorFlow TFLite export was not run because no trained in-memory model was provided in this sandbox.
- Real Export Validation was not run because no `.tflite` model and loaded dataset were provided in this sandbox.

## Known limits / next steps

- This patch is intended to make normal successful TFLite export/validation quiet in the terminal.
- A small number of TensorFlow messages can still appear if TensorFlow is imported by third-party code before piTrainer enters its suppression context.
- The current TensorFlow bundled Lite interpreter still works for now, but future TensorFlow versions may prefer the separate LiteRT package. That is not urgent unless TensorFlow removes the bundled interpreter in a future release.
