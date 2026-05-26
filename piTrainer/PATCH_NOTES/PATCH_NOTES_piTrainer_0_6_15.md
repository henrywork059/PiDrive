# PATCH NOTES — piTrainer_0_6_15 Default Horizontal Flip Preprocess Patch

## Request summary
- Make the default preprocessing recipe include horizontal flip augmentation for all frames.
- Make the Auto Preprocess workflow include horizontal flip augmentation automatically.

## Cause / root cause
The V6.11 Auto Preprocess workflow made preprocessing easier, but the recommended/default recipe still left the mirror/horizontal-flip option disabled. That meant users had to open the Settings tab and manually enable mirrored copies before preprocessing. For normal driving datasets, a left-right horizontal flip copy is a useful standard augmentation because it adds a balanced synthetic frame for every active source frame while inverting the steering label for the flipped copy.

## Files changed
- `piTrainer/piTrainer/panels/preprocess/preprocess_config_panel.py`
  - Enables the horizontal flip/mirror checkbox by default.
  - Keeps `reset_to_defaults()` setting horizontal flip enabled.
  - Updates user-facing text from generic mirroring to horizontal flip copies.
  - Keeps the option inside the collapsed augmentation section so the normal workflow remains simple.
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
  - Updates the Quick Preprocess guide and tooltips to explain that recommended defaults and Auto Preprocess add horizontal flip copies.
- `piTrainer/piTrainer/panels/preprocess/preprocess_summary_panel.py`
  - Updates preview count wording from `mirror` to `flip`.
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
  - Updates result text to describe horizontal flip copies/rows.
  - The existing augmentation logic is preserved: each flipped row has `aug_flip_lr=True`, `aug_variant='mirror'`, and the steering value inverted.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_15_preprocess_default_horizontal_flip`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.15` / `piTrainer_0_6_15`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents that recommended/default/auto preprocessing includes one horizontal flip copy for every active frame.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions to preserve this default/auto horizontal flip behaviour.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_15.md`
  - This patch note.

## Exact behaviour changed
- Opening the Preprocess settings with no saved recipe now starts with `Add one horizontal flip copy for every row` enabled.
- Clicking `Use Recommended Defaults` now enables horizontal flip copies.
- Clicking `Auto Preprocess Active Data` now enables horizontal flip copies before applying preprocessing.
- The active preprocessed dataset now normally contains:
  - the original active rows; and
  - one horizontally flipped synthetic copy of each active row.
- The flipped synthetic rows keep the same image path but set `aug_flip_lr=True`; the TensorFlow dataset pipeline flips the image during training/validation loading.
- Steering is inverted for each flipped copy, while speed/throttle is preserved.
- Preview/result wording now says horizontal flip/flip rather than generic mirror in the main user-facing text.

## Behaviour intentionally not changed
- PiSD V7 `labels.jsonl` / `records.jsonl` support is unchanged.
- PiSD V7 overlay redraw and saved overlay metadata support are unchanged.
- Hidden/soft-deleted rows remain excluded from active dataframes, preprocessing, training, validation, and TensorFlow dataset creation.
- Auto Preprocess still does not require saving the preprocessed dataset to disk before training.
- Horizontal flip still creates synthetic dataframe rows; it does not physically duplicate or rewrite image files.
- Existing saved preprocessing settings can still override the default if the user previously saved a custom recipe with horizontal flip disabled.
- Training device/GPU controls from V6.11 are unchanged.
- The sortable model/view Record Preview table from V6.13/V6.14 is unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.14` install.
- Existing PiSD sessions do not need migration.
- Existing saved preprocess settings remain readable. If a saved settings file explicitly has `mirror_enabled: false`, loading that custom saved recipe will still show flip disabled until the user clicks `Use Recommended Defaults` or `Auto Preprocess Active Data`.
- Existing saved/preprocessed datasets are not modified retroactively.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_14` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_14.md`
  - `PATCH_NOTES_piTrainer_0_6_13.md`
  - `PATCH_NOTES_piTrainer_0_6_12.md`
  - `PATCH_NOTES_piTrainer_0_6_11.md`
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
  - V6.14 sortable Record Preview with default `frame_id` sorting.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_14_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Preprocess page, Quick Preprocess actions, Preprocess Recipe controls, preprocess service, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a direct preprocess-service test with a temporary dataframe confirming:
  - enabling `mirror_enabled=True` produces one additional row per active source row;
  - flipped rows have `aug_flip_lr=True`;
  - flipped rows invert steering;
  - flipped rows preserve throttle/speed.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.15`;
  - `PATCH_VERSION` reports `piTrainer_0_6_15`;
  - `FORMAT_VERSION` reports `0_6_15_preprocess_default_horizontal_flip`;
  - `reset_to_defaults()` sets `mirror_enabled` checked;
  - Auto Preprocess still calls `_set_recommended_defaults()` before applying preprocessing.
- Compared the working tree against fresh V6+0.6.1 through 0.6.14 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Direct PySide6 smoke testing was not performed in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow validation/training was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- Horizontal flip doubles the number of active rows when applied. This improves data augmentation but also increases training input size and training time.
- The internal augmentation variant name remains `mirror` for backward compatibility with existing code and saved rows, while user-facing text now describes it as horizontal flip.
