# PATCH NOTES — piTrainer_0_4_9

## Request summary
- Fix preprocessing returning zero active rows for a PiSD V7 recording even though source rows were loaded.
- Preserve the latest accepted trainer layout, green next-step buttons, PiSD V7 overlay redraw, and previous training-start fixes.

## Cause / root cause
The loaded dataset contained 1825 source rows, but preprocessing with `Mode filter: Manual only` reduced the dataset to zero rows.

The immediate cause was the manual-mode detection path:
- PiSD V7 `labels.jsonl` rows are intentionally compact training labels.
- Those rows may not contain a direct `mode` field.
- The session folder and/or manifest still identify the data as `manual_drive`, but preprocessing only checked a narrow mode value path.
- As a result, the Data page could load PiSD V7 label rows correctly, while the Preprocess page could still treat them as non-manual and remove every row.

## Files changed
- `piTrainer/piTrainer/services/data/record_loader_service.py`
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_9.md`

## Exact behavior changed
- PiSD V7 manifest metadata now contributes to the row mode when compact `labels.jsonl` rows do not contain a direct mode field.
- Loaded rows now infer mode from, in order:
  - explicit record mode fields;
  - manifest label / manifest session id;
  - selected session name.
- Preprocess manual filtering is now more robust. It checks manual-drive hints from:
  - `mode`
  - `session_label`
  - `label`
  - `session`
  - `session_id`
- `Manual only` now accepts rows whose metadata or session folder contains `manual`, including PiSD V7 names like `..._manual_drive_...`.
- `Exclude manual` uses the same improved manual detection so the two options remain consistent.

## Verification actually performed
- Applied the patch forward from the accepted `0_4_8` state.
- Created a temporary PiSD V7-style session with:
  - `manifest.json` label set to `manual_drive`;
  - compact `labels.jsonl` row without a direct `mode` field;
  - frame path under `frames/`.
- Verified `load_records_dataframe(...)` loads the row and infers `mode='manual_drive'`.
- Verified `apply_preprocessing_recipe(...)` with `Mode filter: Manual only` and `Require existing images: Yes` keeps the row instead of filtering it to zero.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`

## Rollback-risk check
- Checked the latest patch note `0_4_8` and previous three notes `0_4_7`, `0_4_6`, and `0_4_5`.
- Preserved the `0_4_8` green next-step button presentation and collapse defaults.
- Preserved the `0_4_7` full-width splitter layout.
- Preserved the `0_4_6` training-start preflight and split refresh logic.
- Preserved the `0_4_5` sorted-table and JSONL edit/delete fixes.
- No older file copy was restored over the current accepted state.

## Known limits / next steps
- If preprocessing still returns zero rows after this patch, the next likely cause is missing image files after copying/downloading a recording folder. In that case, turn off `Require existing images` only for diagnosis, or reload the full session folder including the `frames/` subfolder.
- Full GUI training was not run inside this sandbox; this patch was verified at service/code level.
