# PATCH NOTES — piTrainer_0_9_7 Data Workflow Tab Order Fix

## Request summary

Fix the Data Workflow tab numbering after the model deploy feature. The user clarified that tab `4` should remain `Review`; the new deploy workflow should not replace or rename the existing review tab.

## Cause / root cause

Patch `0.9.6` inserted the new model deployment panel as Data Workflow tab `4 Deploy` and moved the existing review tools to `5 Review`. That conflicted with the user's established workflow order, where `4` is still the review step.

## Files changed

- `piTrainer/piTrainer/pages/data_page.py`
  - Restores Data Workflow tab `4 Review`.
  - Moves the model deployment workflow to `5 Deploy`.
  - Updates the Data page summary text so it matches the corrected order.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.7 / piTrainer_0_9_7`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_7.md`
  - Adds this patch note.

## Exact behavior changed

The Data Workflow tabs are now ordered as:

1. `1 Load`
2. `2 Hide & Recover`
3. `3 Filter`
4. `4 Review`
5. `5 Deploy`

The deploy feature from `0.9.6` is preserved. Only the workflow tab order and visible naming were corrected.

## Rollback safety check

Checked against the accepted `0.9.4`, `0.9.5`, and `0.9.6` patch notes and current code. This patch does not remove:

- the `0.9.4` wording/table-header cleanup
- the `0.9.5` arrow-key focus fix
- the `0.9.6` model deployment, diff sorting, deploy overlay, or apply-to-selected feature

## Verification performed

- Applied on top of the accepted `0.9.6` state.
- Confirmed `data_page.py` now contains `4 Review` before `5 Deploy`.
- Ran Python compile validation for `piTrainer` and `main.py`.
- Ran AST parse validation for all Python files in the patched project.
- Built a patch-only zip and checked its contents.

## Known limits / next steps

- This patch only corrects workflow tab order and wording. It does not change the model deploy backend logic from `0.9.6`.
