# PATCH NOTES — piTrainer_0_6_17 Training Default Split and Epoch Patch

## Request summary
- Change the training split default to random rows.
- Change the default epoch count to 100.

## Cause / root cause
- The previous training defaults still opened with `By session` and 10 epochs.
- `By session` is useful for some evaluation workflows, but it can be confusing for small classroom/testing datasets and for cases where only one recording session is loaded.
- Random-row splitting gives most users an immediate train/validation split from the active rows without needing to understand session grouping first.
- 10 epochs is often too low as a default for the lightweight steering/speed model workflow, so the default is now 100 while early stopping remains enabled.

## Files changed
- `piTrainer/piTrainer/app_state.py`
  - Changes `TrainConfig.epochs` default from `10` to `100`.
  - Changes `TrainConfig.session_split` default from `True` to `False`.
  - Changes `TrainConfig.split_mode` default from `By session` to `Random rows`.
- `piTrainer/piTrainer/panels/train/train_config_panel.py`
  - Changes the split-mode combo fallback/default to `Random rows`.
- `piTrainer/piTrainer/services/train/split_service.py`
  - Changes split-service fallback behaviour to random-row splitting when split mode is missing or blank.
  - Keeps explicit `By session` available when the user selects it.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_17_training_random_rows_defaults`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.17` / `piTrainer_0_6_17`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the accepted training defaults.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve the new training defaults.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_17.md`
  - This patch note.

## Exact behaviour changed
- New app state now starts with:
  - `split_mode = "Random rows"`;
  - `session_split = False`;
  - `epochs = 100`.
- The Train Config panel now opens with `Random rows` selected by default.
- If older or partial code/config objects do not provide `split_mode`, the split service now falls back to random rows rather than session splitting.
- Explicit user selection of `By session` or `Sequential rows` still works.
- Early stopping remains enabled, so 100 is the upper limit unless the model stops early.

## Behaviour intentionally not changed
- Validation ratio remains unchanged.
- Batch size remains unchanged.
- Training device default remains `Auto (GPU if available)`.
- GPU/CPU training controls from V6.11 are unchanged.
- Auto Preprocess and default horizontal flip augmentation from V6.15/V6.16 are unchanged.
- Horizontal-flip rows still invert steering and preserve speed/throttle.
- Hidden/soft-deleted frames remain excluded from preprocessing, training, validation, and TensorFlow dataset creation.
- Record Preview table sorting and `frame_id` first-column behaviour are unchanged.
- PiSD V7 labels/records/overlay support is unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.16` install.
- Existing loaded sessions and PiSD recordings do not need migration.
- If the user manually changes the Train Config panel after launch, their selected split mode and epoch count for that run still override the defaults.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_16` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_16.md`
  - `PATCH_NOTES_piTrainer_0_6_15.md`
  - `PATCH_NOTES_piTrainer_0_6_14.md`
  - `PATCH_NOTES_piTrainer_0_6_13.md`
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
  - V6.16 horizontal-flip steering label guard.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_16_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Train Config panel, TrainConfig defaults, split service, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a direct split-service check confirming:
  - default `TrainConfig()` uses `Random rows`;
  - default `TrainConfig()` uses `epochs=100`;
  - random-row split produces both train and validation rows for a multi-row dataframe.
- Compared the working tree against fresh V6+0.6.1 through 0.6.16 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- Random rows is now the default because it is simpler for most users, but `By session` remains available when the user wants a stricter session-level evaluation split.
