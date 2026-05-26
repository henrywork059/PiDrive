# PATCH NOTES — piTrainer_0_6_16 Horizontal Flip Steering Label Guard Patch

## Request summary
- Patch the horizontal flip preprocessing path so that whenever a frame is flipped left/right, the corresponding steering input/label is also flipped.
- Keep speed/throttle unchanged for flipped frames.

## Cause / root cause
- V6.15 already inverted steering when creating default horizontal-flip rows, but the relationship was only handled in the preprocess row-generation block.
- To make the behaviour harder to break later, the flip/steering rule now has a shared guard that is also used by training and validation paths.
- Validation loaded images directly with PIL and did not apply `aug_flip_lr`. That could make validation score an unflipped image against an inverted steering label when augmented rows were present.
- String values loaded from CSV/JSONL, such as `"False"`, should not be treated as truthy flip flags.

## Files changed
- `piTrainer/piTrainer/services/data/augmentation_service.py`
  - New shared helper service for boolean flip flag parsing and horizontal-flip label safety.
  - Adds `truthy_value()`, `boolean_series()`, and `normalize_horizontal_flip_labels()`.
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
  - Adds `_horizontal_flip_copy()` as the single place that creates horizontal-flip synthetic rows.
  - Stores `source_steering` on flipped rows.
  - Sets flipped-row `steering` to `-source_steering`.
  - Preserves throttle/speed values on flipped rows.
  - Marks flipped rows with `aug_flip_lr=True`, `aug_variant='horizontal_flip'`, and `flip_steering_inverted=True`.
  - Runs the shared flip label guard before returning the augmented dataset.
  - Adds preview text stating that horizontal flip inverts steering and preserves speed/throttle.
- `piTrainer/piTrainer/services/train/dataset_service.py`
  - Uses the shared flip label guard before building TensorFlow datasets.
  - Parses `aug_flip_lr` robustly so string `"False"` does not become a flipped image.
- `piTrainer/piTrainer/pages/train_page.py`
  - Applies the shared flip label guard when preparing usable training rows.
- `piTrainer/piTrainer/services/validation/validation_service.py`
  - Applies the shared flip label guard before validation labels are used.
  - Applies the actual left/right image flip for validation rows where `aug_flip_lr` is true.
- `piTrainer/piTrainer/utils/image_utils.py`
  - Allows scaled preview pixmaps to be loaded with a horizontal flip.
  - Includes the flip state in the pixmap cache key.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Displays `aug_flip_lr` rows using a flipped preview image, so the preview image matches the inverted steering label.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_16_flip_steering_label_guard`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.16` / `piTrainer_0_6_16`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the horizontal flip safety rule.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve the flip/steering guard.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_16.md`
  - This patch note.

## Exact behaviour changed
- Horizontal-flip rows now carry traceable source-label metadata:
  - `source_steering`
  - `source_throttle` when available
  - `source_speed` when available
  - `flip_steering_inverted=True`
- Flipped rows always use the opposite steering sign from their source steering when `source_steering` is present.
- Flipped rows preserve throttle/speed.
- Training data preparation and TensorFlow dataset creation re-check flipped rows with the shared guard before labels are used.
- Validation now flips the image for `aug_flip_lr=True` rows and also uses the guarded steering label.
- Image Preview now displays horizontal-flip rows as flipped images, rather than showing the original image against an inverted steering value.
- Boolean parsing for `aug_flip_lr` is safer for CSV/JSONL-style strings such as `True`, `False`, `1`, and `0`.

## Behaviour intentionally not changed
- Auto Preprocess still enables horizontal flip by default, as introduced in V6.15.
- Auto Preprocess still does not require saving the preprocessed dataset to disk before training.
- Horizontal flip still creates synthetic dataframe rows and does not physically duplicate image files.
- Speed/throttle values are not inverted or changed by horizontal flip.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and saved overlay metadata support are unchanged.
- Hidden/soft-deleted rows remain excluded from preprocessing, training, validation, and TensorFlow dataset creation.
- Training device/GPU controls from V6.11 are unchanged.
- Record Preview table layout/sorting from V6.13/V6.14 is unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.15` install.
- Existing PiSD sessions do not need migration.
- Existing saved/preprocessed datasets remain readable.
- New flipped rows use `aug_variant='horizontal_flip'` instead of the older internal `mirror` label. Existing rows with older variant names still work because training/validation check `aug_flip_lr`, not the variant text.
- If an existing saved flipped row has `source_steering`, piTrainer can correct its flipped `steering` label before training/validation use. If no source steering metadata exists, piTrainer keeps the row's existing steering value because it cannot safely infer the original label.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_15` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_15.md`
  - `PATCH_NOTES_piTrainer_0_6_14.md`
  - `PATCH_NOTES_piTrainer_0_6_13.md`
  - `PATCH_NOTES_piTrainer_0_6_12.md`
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
  - V6.15 default/auto horizontal flip preprocessing.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_15_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Preprocess service, Train page, TensorFlow dataset service, Validation service, Image Preview panel, image utility, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran direct preprocess-service tests confirming:
  - enabling horizontal flip adds one flipped row per source row;
  - flipped rows store `source_steering`;
  - flipped rows set `steering=-source_steering`;
  - flipped rows preserve `throttle`/speed;
  - flipped rows set `flip_steering_inverted=True`.
- Ran direct augmentation-service tests confirming:
  - string `"False"` is parsed as false;
  - string `"True"` is parsed as true;
  - a stale flipped row with `source_steering` is corrected back to inverted steering.
- Ran a direct validation input test with a temporary image confirming:
  - `aug_flip_lr=True` rows are horizontally flipped before validation;
  - validation target steering is corrected from `source_steering`;
  - validation target speed/throttle is preserved.
- Compared the working tree against fresh V6+0.6.1 through 0.6.15 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Direct PySide6 smoke testing was not performed in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- Existing older saved flipped rows without `source_steering` cannot be automatically corrected because the original steering value is not traceable. New V6.16 flipped rows include `source_steering` to avoid that ambiguity.
- Editing synthetic flipped rows from the preview still needs care because the physical image file is shared with the source row. A future patch could make synthetic augmentation rows read-only in Data Review if live testing shows accidental edits are confusing.
