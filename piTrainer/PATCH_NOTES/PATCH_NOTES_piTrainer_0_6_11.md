# PATCH NOTES — piTrainer_0_6_11 Preprocess Auto Workflow and GPU Device Patch

## Request summary
- Remake the Preprocess page layout so the workflow is easier for most users to follow.
- Rearrange windows, panels, buttons, and controls.
- Add Auto and Default functions/buttons so users can preprocess data with fewer clicks.
- Keep more advanced preprocessing settings more collapsed by default.
- Allow training to run on GPU when available.

## Cause / root cause
The V6.10 Preprocess page still required users to understand two separate tabs (`Source` and `Recipe`) and then choose the correct preview/apply buttons from a general action panel. That was powerful, but it made the common path feel too manual: a normal user needed to inspect the source, preview a recipe, apply it, and understand several advanced controls before getting usable preprocessed data.

Training also relied on TensorFlow's default device placement without exposing a user-facing training-device choice or clear logs. TensorFlow can use GPU automatically when the installed TensorFlow build and drivers expose one, but piTrainer did not make this visible or controllable.

## Files changed
- `piTrainer/piTrainer/pages/preprocess_page.py`
  - Rebuilds the Preprocess workspace around a simpler left-to-right workflow.
  - Replaces the old `1 Source` / `2 Recipe` workflow tabs with `1 Auto` / `2 Settings`.
  - Replaces the always-visible vertical preview/log stack with `Preprocess Review` tabs: `1 Preview` / `2 Log`.
  - Adds `use_recommended_defaults()` and `auto_preprocess()` helpers.
  - Makes the page banner focus the new green `Auto Preprocess Active Data` button.
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
  - Reworks the action panel into `Quick Preprocess`.
  - Adds `Auto Preprocess Active Data` as the main green one-click action.
  - Adds amber setup buttons for `Use Recommended Defaults` and `Preview Current Recipe`.
  - Keeps `Confirm Current Recipe` for custom settings.
  - Moves reset/save/sync tools into a collapsed `Save + maintenance` section.
- `piTrainer/piTrainer/panels/preprocess/preprocess_filter_panel.py`
  - Clarifies guidance text.
  - Labels deeper filters as advanced collapsed sections.
- `piTrainer/piTrainer/panels/preprocess/preprocess_config_panel.py`
  - Makes output image size the first visible recipe section.
  - Moves turning boost and mirror/color controls into advanced collapsed sections.
- `piTrainer/piTrainer/panels/preprocess/preprocess_result_panel.py`
  - Updates placeholder text for the new auto/preview workflow.
- `piTrainer/piTrainer/app_state.py`
  - Adds `TrainConfig.compute_device` with default `Auto (GPU if available)`.
- `piTrainer/piTrainer/panels/train/train_config_panel.py`
  - Adds a `Training device` combo box with `Auto (GPU if available)`, `CPU only`, and `GPU only`.
  - Keeps device/review options visible while deeper dataset options stay collapsed.
- `piTrainer/piTrainer/services/train/worker.py`
  - Configures TensorFlow device behaviour inside the worker after importing TensorFlow.
  - Logs GPU availability and selected device mode.
  - Supports CPU-only mode by hiding GPU devices when possible.
  - Supports GPU-only mode by failing early if TensorFlow cannot detect a GPU.
  - Enables GPU memory growth where available.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to reset saved layout state for the redesigned Preprocess page.
- `piTrainer/piTrainer/version.py`
  - Updates visible version metadata to `0.6.11` / `piTrainer_0_6_11`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the new Preprocess workflow and training-device/GPU rules.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions so the new Preprocess auto path and GPU device controls are preserved.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_11.md`
  - This patch note.

## Exact behaviour changed
- Preprocess now opens around the normal user path:
  - `1 Auto` contains `Source Summary` and `Quick Preprocess`.
  - `2 Settings` contains optional source filters and recipe/image-size controls.
- The main green button is now `Auto Preprocess Active Data`.
  - It loads the recommended safe defaults.
  - It applies preprocessing immediately to the loaded source data.
  - It updates the active training dataset and synced train image size in one action.
- `Use Recommended Defaults` is an amber setup action.
  - It resets the recipe to the safe default values.
  - It previews the expected row counts without applying them.
- `Preview Current Recipe` remains an amber prerequisite/setup action for users who customise settings.
- `Confirm Current Recipe` remains available for users who intentionally use custom settings.
- Save/reset/sync tools are still available but no longer compete with the main workflow; they are inside collapsed `Save + maintenance`.
- The review area now uses tabs:
  - `1 Preview` for current dataset/preprocess results;
  - `2 Log` for detailed logs.
- Advanced preprocess controls are deeper and collapsed by default:
  - frame thinning;
  - steering/speed ranges;
  - straight-row balancing;
  - turning boost;
  - mirror/color variants.
- Training config now has a user-facing `Training device` option:
  - `Auto (GPU if available)` uses TensorFlow's visible GPU devices when available;
  - `CPU only` attempts to hide GPU devices before building datasets/models;
  - `GPU only` stops early with a clear error if no GPU is detected.

## Behaviour intentionally not changed
- PiSD V7 `labels.jsonl` / `records.jsonl` support is unchanged.
- PiSD V7 overlay redraw and saved overlay metadata support are unchanged.
- Hidden/soft-deleted rows remain excluded from active dataframes, preprocessing, training, validation, and TensorFlow dataset creation.
- Data Workflow tab order remains `1 Load`, `2 Manage`, `3 Review`.
- Data Review tab order remains `1 Records`, `2 Stats`, `3 Plot`.
- Record Preview multi-select, first-column anchoring, Up/Down cycling, and Select All Visible Frames are unchanged.
- Bulk Edit Selected Frames remains in `3 Review`, remains one-field-at-a-time, and keeps the checkbox plus final warning dialog.
- The V6.10 targeted single-frame edit optimisation and JSONL parse cache are unchanged.
- Training still defers TensorFlow import to the worker thread so the app can start without TensorFlow installed.
- TensorFlow still performs the real model training path; this patch only adds device selection and logging.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.10` install.
- Existing PiSD sessions and preprocessed datasets do not need migration.
- Existing training config state will default to `Auto (GPU if available)` if no saved device choice exists.
- GPU acceleration still depends on the local TensorFlow installation, GPU hardware, drivers, and platform support. The new controls expose and log the choice; they do not install GPU drivers or replace TensorFlow.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_10` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_10.md`
  - `PATCH_NOTES_piTrainer_0_6_9.md`
  - `PATCH_NOTES_piTrainer_0_6_8.md`
  - `PATCH_NOTES_piTrainer_0_6_7.md`
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
  - V6.4 first-column anchoring intent and removal of `Next Step:` / `Show:` prefixes;
  - V6.5 central theme token system;
  - V6.6 amber/green action colour semantics and centred steering slider;
  - V6.7 Bulk Edit Selected Frames panel and one-field-at-a-time edit safety;
  - V6.8 traceable soft-delete / hidden-frame behaviour;
  - V6.9 fast batch JSONL bulk-edit path;
  - V6.10 Record Preview anchoring, Up/Down cycling, Bulk Edit Select All, and edit optimisation.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_10_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the current Preprocess page, preprocess panels, train config panel, training worker, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.11`;
  - `PATCH_VERSION` reports `piTrainer_0_6_11`;
  - `FORMAT_VERSION` reports `0_6_11_preprocess_auto_gpu_layout`;
  - Preprocess workflow contains `1 Auto` and `2 Settings`;
  - Preprocess review contains `1 Preview` and `2 Log`;
  - `Auto Preprocess Active Data`, `Use Recommended Defaults`, and `Preview Current Recipe` are present;
  - `TrainConfig.compute_device` exists;
  - `Training device` options include Auto, CPU only, and GPU only;
  - the training worker contains TensorFlow GPU detection/device logging logic.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4+0.6.5+0.6.6+0.6.7+0.6.8+0.6.9+0.6.10 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Direct PySide6 import/smoke testing was not possible because this sandbox does not have PySide6 installed.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run.
- GPU hardware execution was not tested in this sandbox.

## Known limits / next steps
- GPU training is available only when the user's local TensorFlow build can see a compatible GPU. On many modern Windows setups, this may require a supported TensorFlow/GPU environment outside piTrainer itself.
- `Auto Preprocess Active Data` intentionally uses the safe default recipe. Users who want balancing, thinning, or augmentation should use `2 Settings`, preview, and then confirm the current recipe.
- A later patch could add a visual one-line checklist under `Quick Preprocess` if the live GUI review shows users still need more guidance.
