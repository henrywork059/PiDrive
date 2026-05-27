# PATCH NOTES — piTrainer_0_7_1 Horizontal Flip Label Safety Review Patch

## Request summary
- Review piTrainer flip/augmentation paths so horizontal-flipped data is label-safe.
- Ensure that when a frame is flipped, the steering label is also inverted.
- Ensure the same rule is used for preprocessing, training, validation, and frame review/preview displays.

## Cause / root cause
- V7 already generated horizontal flip augmentation with inverted steering and training/validation loaders already called the shared label normaliser.
- However, the review found two remaining risk areas:
  - the shared normaliser only corrected flipped rows when `source_steering` was present, so older saved preprocessed rows without that column could remain unverified;
  - training epoch review and validation frame review could display the original unflipped image while comparing against the flipped/inverted label, creating confusing visual feedback even though the TensorFlow training/validation input pipeline handled flipped images.

## Files changed
- `piTrainer/piTrainer/services/data/augmentation_service.py`
  - Strengthens `normalize_horizontal_flip_labels()` into the central label-safety guard.
  - Uses `source_steering` as the primary source of truth for flipped rows.
  - Falls back to matching an unflipped source row by `source_frame_id`/`frame_id` for older datasets missing `source_steering`.
  - Re-applies `source_throttle` / `source_speed` when present so horizontal flip cannot accidentally alter speed/throttle.
  - Adds trace columns such as `flip_label_source` and `flip_label_warning` where needed.
- `piTrainer/piTrainer/services/train/worker.py`
  - Applies the shared flip-label guard to epoch-review samples.
  - Flips review images when `aug_flip_lr=True` before model prediction.
  - Sends flip metadata to the Train epoch review panel.
- `piTrainer/piTrainer/panels/train/train_epoch_review_panel.py`
  - Displays flipped images when `aug_flip_lr=True`.
  - Shows horizontal-flip/source metadata in the review card.
- `piTrainer/piTrainer/services/validation/validation_service.py`
  - Keeps using the shared flip-label guard before validation.
  - Adds flip/source metadata to validation result payloads so review panels can display the correct image orientation.
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
  - Displays flipped images when `aug_flip_lr=True`.
  - Shows horizontal-flip/source metadata and warnings in the validation preview.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.7.1` / `piTrainer_0_7_1`.
- `piTrainer/AGENTS.md`
  - Adds a stronger future anti-rollback rule for the shared horizontal-flip label guard.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents that training, validation, train review, and validation review must all use the same flipped-image/flipped-label rule.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_7_1.md`
  - This patch note.

## Exact behaviour changed
- Any row with `aug_flip_lr=True` and a valid `source_steering` is forced to use:
  - `steering = -source_steering`
  - `flip_steering_inverted=True`
- If `source_steering` is missing but `source_frame_id` matches an unflipped row's `frame_id`, the source row's steering is used and inverted.
- If a flipped row cannot be proven label-safe, piTrainer does not guess or double-invert it; it marks `flip_label_warning` for inspection.
- If `source_throttle` / `source_speed` are present, they are re-applied to the flipped row so speed/throttle stay unchanged.
- Train epoch review now predicts and displays the flipped image for `aug_flip_lr=True` rows.
- Validation review now displays the flipped image for `aug_flip_lr=True` rows.
- Validation result rows now carry flip/source metadata through to the frame review panel.

## Behaviour intentionally not changed
- Auto/default preprocessing still includes one horizontal flip copy for every active frame.
- Synthetic rows still use `s_` frame IDs.
- Original source rows still keep their original `frame_id`.
- Training split default remains random rows.
- Default epochs remain `100`.
- Three-column Train and Validation layouts are preserved.
- Export behaviour and TensorFlow CPU/GPU selection logic are unchanged.
- Hidden/soft-deleted rows remain excluded from preprocessing, training, validation, and TensorFlow dataset creation.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V7 / `piTrainer_0_7_0` install.
- Existing saved preprocessed datasets with `source_steering` will be corrected/guarded at training and validation time.
- Older saved datasets missing `source_steering` can be recovered when the matching unflipped source row is present in the same dataframe.
- Older flipped rows that cannot be matched safely are not silently changed; they are marked with `flip_label_warning`.
- Re-running Auto Preprocess from V7.1 is still the cleanest way to regenerate fully traceable flipped rows.

## Rollback-risk check
- Built forward from full `piTrainer_0_7_0` V7 baseline.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous three relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_7_0.md`
  - `PATCH_NOTES_piTrainer_0_6_20.md`
  - `PATCH_NOTES_piTrainer_0_6_19.md`
  - `PATCH_NOTES_piTrainer_0_6_18.md`
- Confirmed this patch does not intentionally roll back:
  - V7 version-line packaging rules;
  - export log clarity from `0.6.20`;
  - three-column Validation layout from `0.6.19`;
  - synthetic `s_` IDs and Train three-column layout from `0.6.18`;
  - horizontal-flip default preprocessing and steering inversion from `0.6.15` / `0.6.16`.

## Verification actually performed
- Inspected the current V7 flip-related code paths:
  - preprocessing flip generation;
  - shared augmentation/label guard;
  - TensorFlow training dataset creation;
  - training-start row cleaning;
  - train epoch review sample preparation;
  - validation input preparation;
  - validation frame review display;
  - Data image preview display.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran direct label-guard tests confirming:
  - `aug_flip_lr=True` rows invert `source_steering`;
  - throttle/speed are preserved from source values;
  - older rows missing `source_steering` can recover from matching `source_frame_id`;
  - unverified flipped rows are warning-marked rather than guessed.
- Ran a validation-preparation test with a temporary left/right image confirming:
  - validation flips the image when `aug_flip_lr=True`;
  - validation target steering is inverted for the flipped row;
  - validation preview rows carry the flip flag and negative target steering.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Full TensorFlow training/validation was not run.
- Real PiSD recording import was not re-run in this sandbox.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- If a previously saved dataset contains only flipped rows, has no `source_steering`, and has no matching unflipped source row, piTrainer cannot safely know whether the stored steering is already inverted. It now marks that condition instead of silently guessing.
- For the cleanest dataset, re-run Auto Preprocess after installing this patch so flipped rows include full source metadata.
