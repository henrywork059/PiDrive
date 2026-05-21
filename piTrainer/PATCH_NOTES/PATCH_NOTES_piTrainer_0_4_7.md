# PATCH NOTES — piTrainer_0_4_7

## Request summary
- Fix the trainer window layout so the visible left / middle / right sections always fill the whole window width.
- Avoid the current dock behaviour where the user has to drag/extend the right side to reveal or enlarge content.
- Let users adjust proportions only by dragging visible dividers between sections.
- Apply the change across the whole programme while preserving the PiSD V7 data/overlay work and recent training-start fixes.

## Cause / root cause
- The `0_4_1`–`0_4_3` layout patches improved readability by grouping controls into scrollable/collapsible workflow sidebars, but the main page structure still used `QDockWidget` and nested dock splitting.
- Docked panels are flexible, but they can leave unusable filler/edge space and may require the user to drag a dock boundary outward before the right-side content becomes readable.
- For the trainer workflow, the safer default is a fixed visible workspace structure where every page always occupies the available width and the only layout adjustment is splitter proportion dragging.

## Files changed
- `piTrainer/piTrainer/pages/dock_page.py`
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
- `piTrainer/piTrainer/ui/styles.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_7.md`

## Exact behaviour changed
- Replaced the default page workspace layout with full-width `QSplitter` workspaces.
- Added reusable splitter helpers in `DockPage`:
  - `make_panel_frame()` wraps a panel with a readable title frame.
  - `make_horizontal_splitter()` creates the main left/right or left/middle/right workspace.
  - `make_vertical_splitter()` creates stacked result/log/plot areas inside the right side.
- Data page now uses a full-width three-section layout:
  - left: `Data Workflow`
  - middle: `Record Preview`
  - right: `Image Preview + V7 Overlay` stacked above `Data Plot`
- Preprocess page now uses a full-width splitter layout:
  - left: `Preprocess Workflow`
  - right: `Preprocess Preview` stacked above `Preprocess Log`
- Train page now uses a full-width splitter layout:
  - left: `Training Workflow`
  - right: `Epoch Frame Review` stacked above tabbed `Training History / Log`
- Validation page now uses a full-width splitter layout:
  - left: `Validation Workflow`
  - right: `Validation Frame Review` stacked above tabbed `Validation Plot / Log`
- Export page now uses a full-width splitter layout:
  - left: `Export Workflow`
  - right: `Export Log`
- Splitter handles are visible and styled so users know where to drag to adjust proportions.
- Splitter states are saved/restored under a new layout version key: `0_4_7_full_width_splitter_layout`.
- The old dock-based custom layout is bypassed so cramped previous layouts do not override the new full-width default.

## Compatibility notes
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay metadata and overlay redraw behaviour are unchanged.
- The `0_4_6` training-start fixes are unchanged.
- The `0_4_5` sorted table selection and PiSD V7 edit/delete fixes are unchanged.
- Collapsible/scrollable workflow controls from the previous UI patches are preserved.
- Legacy `add_panel()` support remains in `DockPage` for older or experimental pages, but current pages now use splitter workspaces by default.

## Rollback-risk check
- Checked the latest patch note `0_4_6` and previous three V4 patch notes: `0_4_5`, `0_4_4`, and `0_4_3`.
- Preserved the `0_4_6` training preflight and PiSD `manual_drive` preprocessing fix.
- Preserved the `0_4_5` data edit/delete and sorted preview selection fixes.
- Preserved the `0_4_4` Export Options startup fix.
- Preserved the `0_4_3` programme-wide readability styling, guided workflow labels, and collapsible/scrollable panel presentation.
- No older file copy was restored over the current accepted state.

## Verification actually performed
- Reconstructed the latest piTrainer state from the current `0_4_6` patched folder.
- Ran `python3 -m compileall -q main.py piTrainer` successfully.
- Checked the page files to confirm the previous `splitDockWidget(...)`, `resizeDocks(...)`, and `tabifyDockWidget(...)` default layout calls were removed from the current main pages.
- Removed generated `__pycache__` folders before packaging.
- Packaged only changed files plus this patch note, preserving the exact `piTrainer/...` folder structure.

## Verification not performed
- A real PySide6 GUI render test was not run inside this sandbox because PySide6 is not installed here.
- Full TensorFlow training was not run because this patch changes window layout behaviour only.

## Known limits / next steps
- On Windows, launch the app and drag the visible splitter handles between sections to tune the proportions.
- If any page still feels crowded on a smaller monitor, the next patch can adjust the default splitter ratios without changing data/training behaviour.
