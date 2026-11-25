# piTrainer 0.11.25 — Batch 5 applied preprocessing provenance and plot artifact access

Parent 462681b verified Linux 45619942932 and Windows 45619942897, all five jobs. Reviewed actual main.py, current preprocessing/train/plot code, four notes 0.11.24/23/22/21 and canonical requirements.

## Root cause and changes
The mutable state.preprocess_recipe could be replaced by saving a draft after applying a different recipe. Training never supplied the optional saved preprocessed dataset path. Existing plot paths were selectable but lacked an explicit copy action.
- services/preprocess/applied_binding.py: capture applied recipe by deep copy and exact ordered active metadata fingerprint; return Unknown on mismatch. Saved folder link requires matching recipe and active rows, and expected nonempty files; no automatic linkage to historical folders.
- pages/preprocess_page.py: capture after successful apply, clear on reset/working-folder change, save the captured applied recipe when rows match; retain existing fallback for unmatched rows without asserting provenance.
- pages/train_page.py: pass captured applied recipe and matching saved folder to training snapshot, display confirmed saved run summary path.
- panels/train/train_history_panel.py and panels/validation/validation_plot_panel.py: explicit Copy artifact paths, disabled on empty context; training includes recorded model size and saved run/processed/model paths. No automatic opening of paths.
- tests/test_train_runs_r40.py and test_validation_controls_r35.py: draft mutation, stale row edits, missing saved files, reset and native clipboard/context tests; existing Linux/Windows registration unchanged.
- version.py and shared UI gate updated.

## Verification and limits
Parent exact gate green; new candidate CI pending. Fingerprint is active metadata, not image bytes; saved files checked for existence and nonempty size, not cryptographic revalidation. Unknown on modified metadata is conservative and may omit a valid historical association. No training algorithm, manifest, configuration schema, output naming, six-tab order or inactive component changes. No owner visual approval, actual training or physical deployment. No new proposal closure before exact verification.
