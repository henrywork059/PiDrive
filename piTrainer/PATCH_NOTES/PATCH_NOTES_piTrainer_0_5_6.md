# PATCH NOTES — piTrainer_0_5_6 Data Review Tabs Patch

## Request summary
- Combine the Data page's Record Preview and Data Plot areas.
- Let the user switch between the record table and plot view with tabs, similar to the existing `1 Load`, `2 Review`, `3 Manage` workflow tabs.
- Preserve the full-width splitter layout, compact guided banner, V5.4 panel overflow scrolling, unified formatting, and all PiSD V7 support.

## Cause / root cause
The V5.5 Data page still used a separate vertical right-side stack for `Image Preview + V7 Overlay` and `Data Plot`, while `Record Preview` occupied the middle panel. This made the Data page visually busier than needed and reduced vertical space for both the image overlay and plot. Since the record table and plots are both review/inspection views of the same loaded dataset, they are better grouped as switchable tabs in one central Data Review panel.

## Files changed
- `piTrainer/piTrainer/pages/data_page.py`
  - Replaces the separate right-side `Data Plot` panel with a central `Data Review` tab panel.
  - Adds `1 Records` and `2 Plot` tabs using the same tabbed workflow style already used by the Data Workflow panel.
  - Keeps `Image Preview + V7 Overlay` as the dedicated right-side visual inspection panel.
- `piTrainer/piTrainer/ui/formatting.py`
  - Bumps `FORMAT_VERSION` to `0_5_6_combined_data_review_tabs` so old saved splitter states do not override the new default arrangement.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.5.6` / `piTrainer_0_5_6`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_5_6.md`
  - This patch note.

## Exact behaviour changed
- The Data page now uses this structure:
  - left: `Data Workflow`
  - centre: `Data Review`
    - `1 Records` tab: record table / frame row selection
    - `2 Plot` tab: steering, speed, mode, and session plots
  - right: `Image Preview + V7 Overlay`
- `Data Plot` no longer consumes a separate lower-right splitter area.
- The image preview panel gets the full right-side vertical space.
- Users switch between records and plots using tabs, matching the existing workflow-tab style.
- The app window/status version now reports `0.5.6`.

## Preserved behaviour
- V5.5 compact guided banner and `Show: ...` next-step button behaviour is preserved.
- V5.4 horizontal/vertical overflow scrolling inside reduced panels is preserved.
- V5.2 unified central formatting remains active.
- Full-width splitter workspaces are preserved.
- Green, wide, subtle-pulse real Next Step buttons are preserved.
- PiSD V7 `labels.jsonl` / `records.jsonl` support is preserved.
- PiSD V7 overlay redraw is preserved.
- Preprocessing/manual-drive fixes are preserved.
- Training-start checks are preserved.
- Data loading, editing, deletion, merge, validation, training, and export logic are not changed.

## Rollback-risk check
- Checked the latest V5.5 code state before patching.
- Checked the latest patch notes `0_5_5`, `0_5_4`, and `0_5_3` before patching.
- This patch only changes the Data page presentation layout plus version/layout-version metadata.
- It does not restore older dock layouts.
- It does not remove overflow scrolling, unified formatting, splitters, guided banner behaviour, V7 data loading, V7 overlays, preprocessing fixes, or training-start fixes.

## Verification actually performed
- Built forward from the V5.5 working state.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Checked the Data page source to confirm:
  - `dataReviewTabs` is present;
  - the old `right_stack` Data Plot layout is removed;
  - the centre panel is now `Data Review`.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Full TensorFlow training was not run because this patch changes Data page presentation only.

## Known limits / next steps
- The plot redraw still follows the existing plot-panel refresh behaviour; this patch only changes where the plot is presented.
- If later desired, the `Data Review` tabs can be extended with a third tab for label quality checks or frame metadata.
