# PATCH NOTES — piTrainer_0_6_18 Synthetic Frame IDs and Train Layout Patch

## Request summary
- Give synthetic/preprocessed augmentation rows their own `frame_id` values starting with `s_` so they are visibly different from real source frames.
- Add one more column to the right side of the Train tab.
- Move the epoch frame review to the new right column.

## Cause / root cause
- V6.15/V6.16 added default horizontal flip augmentation and label-safety checks, but synthetic rows still reused the original source frame id. That made the Data/Train review tables harder to read because a real frame and its generated augmentation copy could appear to have the same identity.
- The Train page still used a two-column layout where the frame review sat above the history/log area in a vertical stack. This mixed visual frame inspection with the training curves/logs, making the workflow less clear once training starts.

## Files changed
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
  - Adds synthetic-row identity helpers.
  - Adds `s_`-prefixed `frame_id` values for generated augmentation rows.
  - Adds `source_frame_id`, `is_synthetic=True`, and `synthetic_variant` metadata for synthetic rows.
  - Applies synthetic IDs to horizontal flip rows, colour-variant rows, and turn-boost copies.
  - Keeps original/source rows using their original `frame_id` values.
- `piTrainer/piTrainer/pages/train_page.py`
  - Changes the Train workspace from two columns to three columns.
  - Uses left `Training Workflow`, middle `Training History / Log`, and right `Epoch Frame Review`.
- `piTrainer/piTrainer/panels/train/train_epoch_review_panel.py`
  - Stacks best-fit and worst-fit frame cards vertically so the right-side frame review column remains readable.
- `piTrainer/piTrainer/ui/formatting.py`
  - Adds a central `train_three_panel_workspace` splitter preset.
  - Updates `FORMAT_VERSION` to `0_6_18_synthetic_ids_train_three_columns`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.18` / `piTrainer_0_6_18`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the synthetic-row identity rule and the accepted Train page three-column layout.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve `s_` synthetic frame IDs and the Train page three-column layout.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_18.md`
  - This patch note.

## Exact behaviour changed
- Horizontal flip augmentation rows now have distinct IDs like:
  - `s_frame_000001_horizontal_flip_000001`
- Turn-boost copies now have distinct IDs like:
  - `s_frame_000001_turn_boost_1_000001`
- Colour-variant rows now have distinct IDs like:
  - `s_frame_000001_color_mild_1_000001`
- Generated rows keep a traceable link back to the source frame through `source_frame_id`.
- Generated rows are marked with:
  - `is_synthetic=True`
  - `synthetic_variant=<variant name>`
- Original loaded rows keep their original `frame_id` values and are not prefixed with `s_`.
- The Train page now has three horizontal panels:
  - `Training Workflow`
  - `Training History / Log`
  - `Epoch Frame Review`
- The epoch best/worst frame review is now in the rightmost panel instead of above the history/log panel.

## Behaviour intentionally not changed
- Horizontal flip rows still invert steering and preserve speed/throttle.
- `source_steering`, `source_throttle`, and `source_speed` handling from V6.16 is preserved.
- Training/validation still use the source image path plus augmentation metadata; synthetic rows do not create or require extra image files on disk.
- Default preprocessing still includes horizontal flip augmentation.
- Training split still defaults to random rows.
- Default epochs remain `100`.
- Record Preview still keeps `frame_id` as the first column and default sorting by `frame_id`.
- Hidden/soft-deleted rows remain excluded from preprocessing, training, validation, and TensorFlow dataset creation.
- PiSD V7 labels/records/overlay support is unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.17` install.
- Existing original PiSD session files do not need migration.
- Existing already-saved preprocessed datasets from earlier versions may still contain synthetic rows with reused original IDs. Re-run preprocessing with V6.18 to generate the new `s_` synthetic IDs.
- Existing saved layouts may reset because `FORMAT_VERSION` changed.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_17` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_17.md`
  - `PATCH_NOTES_piTrainer_0_6_16.md`
  - `PATCH_NOTES_piTrainer_0_6_15.md`
  - `PATCH_NOTES_piTrainer_0_6_14.md`
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
  - V6.17 random-row training split and 100-epoch defaults.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_17_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current preprocess service, Train page, epoch frame review panel, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a direct preprocess-service test with sample rows confirming:
  - original rows keep non-`s_` frame IDs;
  - horizontal flip rows get `s_` frame IDs;
  - turn-boost rows get `s_` frame IDs;
  - colour-variant rows get `s_` frame IDs;
  - synthetic rows keep `source_frame_id`;
  - horizontal flip rows still invert steering and preserve throttle.
- Compared the working tree against fresh V6+0.6.1 through 0.6.17 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- Previously saved preprocessed datasets will not be automatically rewritten. Re-run preprocessing to regenerate synthetic IDs.
- The Train page three-column layout is compile/AST/static verified but should still be visually checked in the live Windows GUI.
