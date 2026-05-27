# PATCH NOTES — piTrainer_0_7_2 Synthetic Data Visibility and Edit Redirect Patch

## Request summary
- Continue patching from V7.
- Hide preprocessing-created/generated data from the Data page record list by default.
- Keep generated rows available for training/validation.
- Make `Edit in Data` redirect back to the Data page.
- When the reviewed row is a generated/synthetic datum hidden from Data review, redirect the edit target to the original source frame instead.

## Cause / root cause
- V7 correctly creates synthetic preprocessing rows with their own `s_` frame IDs and keeps them in the active preprocessed dataset for training.
- Because the Data page refreshed directly from `state.filtered_df`, those generated rows also appeared in the Record Preview by default after preprocessing.
- That made the Data page feel cluttered and could invite editing a generated copy instead of the real source label.
- Validation frame review already had an `Edit in Data` button, but a synthetic validation row could point to its hidden `s_` row rather than the original source row.

## Files changed
- `piTrainer/piTrainer/services/data/visibility_service.py`
  - Adds synthetic-row detection helpers:
    - `is_synthetic_record()`;
    - `synthetic_row_mask()`;
    - `without_synthetic_rows()`.
  - Synthetic detection uses trace metadata such as `is_synthetic`, `frame_id` beginning with `s_`, and non-original augmentation variants.
- `piTrainer/piTrainer/pages/data_page.py`
  - Uses `without_synthetic_rows()` for Data-page Record Preview source rows.
  - Keeps `state.filtered_df` unchanged so Train and Validate still use generated rows.
  - Adds source-record lookup for synthetic rows using `source_frame_id`, with fallbacks for shared source image/timestamp.
  - Redirects synthetic focus requests to the matching original source row where possible.
- `piTrainer/piTrainer/main_window.py`
  - Keeps `Edit in Data` switching to the Data page.
  - Shows a clearer status message when a generated validation row has been redirected to its original source frame.
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
  - Updates help text and tooltip to explain that generated validation rows open their original source frame for editing.
- `piTrainer/piTrainer/pages/preprocess_page.py`
  - Updates the preprocess completion message to explain that Train uses all active preprocessed rows while Data Review hides generated rows by default.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.7.2` / `piTrainer_0_7_2`.
- `piTrainer/AGENTS.md`
  - Adds the V7.2 synthetic-data visibility and edit-redirection rule for future AI-agent work.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the accepted Data Review behaviour for generated/synthetic rows.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_7_2.md`
  - This patch note.

## Exact behaviour changed
- After preprocessing, generated rows remain in `state.filtered_df` and continue to be available to Train and Validate.
- Data page Record Preview hides generated/synthetic rows by default.
- Generated rows are identified by metadata such as:
  - `is_synthetic=True`;
  - `frame_id` starting with `s_`;
  - `synthetic_variant` / non-original `aug_variant`.
- Data page plots now follow the same default review set shown in Record Preview, so the review display focuses on original source rows.
- Validation `Edit in Data` still switches to the Data page.
- If the validation row is generated/synthetic, the Data page tries to open the matching original source frame using `source_frame_id` first.
- If a safe source row is found, the status bar reports that the generated row was redirected to the original source frame.
- If the original source row cannot be found, the app fails gracefully with the existing “could not open” status rather than silently editing a hidden generated copy.

## Behaviour intentionally not changed
- Synthetic rows are not removed from the active preprocessed training dataset.
- Train and Validate still use generated rows unless those rows also carry hidden/delete flags.
- Horizontal flip rows still invert steering and preserve speed/throttle.
- Synthetic/generated rows still keep their own `s_` frame IDs and source metadata.
- Record Preview still keeps `frame_id` as the first column, default sorting by `frame_id`, multi-select, soft-hide/delete, and bulk edit support.
- Validation page remains a three-column layout.
- Train page remains a three-column layout.
- Export behaviour, TensorFlow device handling, and CPU/GPU selection are unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V7 install with `piTrainer_0_7_1_patch.zip` applied.
- Existing preprocessed rows are supported if they have `is_synthetic`, `s_` IDs, `source_frame_id`, `synthetic_variant`, or non-original `aug_variant` metadata.
- If an older synthetic row has no reliable source metadata, piTrainer cannot safely know which real source row it came from, so `Edit in Data` may not be able to redirect it.

## Rollback-risk check
- Built forward from full `piTrainer_0_7_0` V7 baseline plus accepted `piTrainer_0_7_1_patch.zip`.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous three relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_7_1.md`
  - `PATCH_NOTES_piTrainer_0_7_0.md`
  - `PATCH_NOTES_piTrainer_0_6_20.md`
  - `PATCH_NOTES_piTrainer_0_6_19.md`
- Confirmed this patch does not intentionally roll back:
  - V7 baseline/version rules;
  - V7.1 horizontal-flip label safety and review display fixes;
  - V6.20 export log clarity;
  - V6.19 Validation three-column layout;
  - V6.18 synthetic `s_` IDs and Train three-column layout;
  - soft-delete hidden-frame behaviour;
  - Record Preview model/view table and first-column behaviour;
  - random-row training split and 100-epoch defaults.

## Verification actually performed
- Applied `piTrainer_0_7_1_patch.zip` over a fresh `piTrainer_0_7_0` tree before editing.
- Inspected current Data page refresh/focus flow, Preprocess apply flow, Validation `Edit in Data` callback path, synthetic metadata generation, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran direct pandas tests confirming:
  - real rows remain visible;
  - rows with `is_synthetic=True` are hidden from Data review by default;
  - rows with `frame_id` beginning `s_` are hidden from Data review by default;
  - rows with non-original augmentation variants are hidden from Data review by default;
  - `without_synthetic_rows()` does not mutate the source dataframe.
- Static-checked changed source files and version strings.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- If a generated row from an older saved dataset has no `source_frame_id`, no usable original frame ID, and no matching source image/timestamp in the active Data set, the app cannot safely redirect it to an original row.
- A future UI option could add a manual “display generated rows” toggle if you later want to inspect every synthetic row inside Data Review, but this patch keeps generated rows hidden by default as requested.
