# PATCH NOTES — piTrainer_0_6_20 Export Log Clarity and TFLite Message Patch

## Request summary
- Review the export behaviour after TensorFlow printed `Saved artifact`, endpoint, TFLite converter warning, and quantization diagnostic messages during export.
- Make the export workflow clearer so users can tell whether export succeeded and which messages are non-fatal TensorFlow converter chatter.

## Cause / root cause
- TensorFlow/Keras/TFLite conversion can print internal messages to stdout/stderr while exporting from a Keras model, including temporary SavedModel endpoint summaries and converter diagnostics.
- The export did create `.keras` and `.tflite` files, but the raw console output looked like an app bug because piTrainer did not summarise the export result clearly.
- The old checkbox text `INT8 quantize TFLite` could be misleading because the current PiDrive-compatible export keeps model input/output as float32 while using TensorFlow Lite size optimisation internally.

## Files changed
- `piTrainer/piTrainer/services/export/export_service.py`
  - Adds `ExportArtifact` result summaries with path, kind, file size, and notes.
  - Captures/summarises TensorFlow/Keras/TFLite export stdout, stderr, and Python warnings where possible.
  - Keeps TFLite size optimisation behaviour but logs that the current PiDrive runtime keeps float32 input/output.
  - Adds TensorFlow export logger configuration to reduce converter noise.
- `piTrainer/piTrainer/pages/export_page.py`
  - Logs created artifacts with type and file size.
  - Logs short explanatory notes instead of leaving the user to interpret raw TensorFlow messages.
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
  - Renames the option label from `INT8 quantize TFLite` to `Reduce TFLite size (quantized, float I/O)`.
  - Adds a tooltip explaining that input/output remain float32 for PiDrive runtime compatibility.
- `piTrainer/piTrainer/__init__.py`
  - Raises the default TensorFlow C++ log level from `2` to `3` to suppress normal INFO/WARNING console chatter during lazy TensorFlow imports.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_20_export_log_clarity`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.20` / `piTrainer_0_6_20`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the Export page message/summary rule.
- `piTrainer/AGENTS.md`
  - Adds an anti-rollback rule for readable export logs and TFLite float-I/O explanation.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_20.md`
  - This patch note.

## Exact behaviour changed
- Export Log now reports entries like:
  - `Created .keras: <path> (<size>)`
  - `Created .tflite: <path> (<size>)`
- When TensorFlow prints temporary SavedModel endpoint information during TFLite conversion, piTrainer summarises it as a note instead of treating it like a visible failure.
- When TensorFlow reports non-fatal TFLite converter diagnostics, piTrainer summarises the relevant outcome.
- Size-optimised TFLite export now explicitly states that float32 input/output is intentional for current PiDrive runtime compatibility.
- Normal TensorFlow INFO/WARNING startup/export chatter should be reduced in PowerShell when TensorFlow is imported through the piTrainer package.

## Behaviour intentionally not changed
- Export still supports `.keras` output.
- Export still supports `.tflite` output.
- Existing base file name and output directory behaviour is unchanged.
- The `_int8` suffix is still used when the size-optimised TFLite option is enabled, so existing deployment expectations are not broken.
- Training, validation, preprocessing, synthetic `s_` IDs, horizontal-flip steering inversion, random-row split defaults, 100-epoch default, and three-column Train/Validation layouts are unchanged.
- No model architecture or trained weights are changed by this patch.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.19` install.
- Existing exported `.keras` and `.tflite` files do not need migration.
- Existing PiSD recordings and preprocessed datasets are not modified.
- If TensorFlow writes directly to the native process stderr at a lower level than Python can capture, some rare converter lines may still appear, but piTrainer now gives a clear Export Log success summary.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_19` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_19.md`
  - `PATCH_NOTES_piTrainer_0_6_18.md`
  - `PATCH_NOTES_piTrainer_0_6_17.md`
  - `PATCH_NOTES_piTrainer_0_6_16.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support;
  - PiSD V7 overlay redraw support;
  - preprocessing/manual-drive fixes;
  - training-start preflight fixes;
  - full-width splitter layout;
  - horizontal overflow scroll behaviour;
  - V6.1 playback-under-preview layout;
  - V6.2 Data Workflow and Data Review tab orders;
  - V6.2 AI-agent instruction document;
  - V6.3 Data Control checkbox and multi-row Record Preview selection;
  - V6.4 label cleanup and first-column anchoring intent;
  - V6.5 central theme token system;
  - V6.6 amber/green action colour semantics and centred steering slider;
  - V6.7 Bulk Edit Selected Frames panel and edit safety;
  - V6.8 traceable soft-delete / hidden-frame behaviour;
  - V6.9 fast batch JSONL bulk-edit path;
  - V6.10 Up/Down cycling, Bulk Edit Select All, and targeted edit optimisation;
  - V6.11 Preprocess auto workflow and training device/GPU controls;
  - V6.12 validation import fix, TensorFlow log handling, and queued edit responsiveness;
  - V6.13 simple model/view Record Preview table;
  - V6.14 sortable Record Preview with default `frame_id` sorting;
  - V6.15 default/auto horizontal flip preprocessing;
  - V6.16 horizontal-flip steering label guard;
  - V6.17 random-row training split and 100-epoch defaults;
  - V6.18 synthetic `s_` frame IDs and Train page three-column layout;
  - V6.19 Validation page three-column layout.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_19_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the current export service, Export page, Export Options panel, TensorFlow log-level setup, latest patch notes, style guide, and AI-agent instructions.
- Inspected the uploaded export artifacts at sandbox level:
  - `picar_model.keras` is a valid Keras zip archive containing `metadata.json`, `config.json`, and `model.weights.h5`.
  - `picar_model_int8.tflite` exists and is approximately 332 KB.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a direct helper test confirming:
  - export artifact sizes format as readable KB/MB labels;
  - captured TensorFlow-style `Saved artifact`, `Ignored output_format`, `fully_quantize`, and quantized-input warning text is reduced to short user-readable notes.
- Compared the working tree against fresh V6+0.6.1 through 0.6.19 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- A full TensorFlow export was not run in this sandbox because TensorFlow is not installed here.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- The uploaded export files suggest export completed, but this patch focuses on app-side clarity and noise reduction rather than changing the trained model.
- A future patch could add an explicit export mode dropdown if you later want separate choices for float32 TFLite, dynamic-range quantized TFLite, and strict full-integer int8 TFLite.
