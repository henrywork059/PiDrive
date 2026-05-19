# PATCH NOTES — piTrainer_0_4_1

## Request summary
- Redesign piTrainer panel positioning because the current pages are difficult to read when many dock panels are squeezed together.
- Collapse less-used panels until clicked.
- Make dense control areas scrollable.
- Reposition major review/preview panels so the main working content has more space.
- Keep the PiSD V7 data and overlay support added in `piTrainer_0_4_0`.

## Design basis / research used
- Qt `QDockWidget` is intended for movable/floating secondary panels around the main workspace, so the redesign keeps dockable major areas but reduces the number of tiny stacked docks.
- Qt `QScrollArea` is intended to show a child widget with scroll bars when its contents exceed the available frame, so dense workflow controls are wrapped in scroll areas.
- Qt `QToolButton` supports arrow display and checkable button behaviour, so it is used as a simple collapsible section header.

## Cause / root cause
- The Data page previously opened seven separate left-side dock panels at once: Session Source, Frame Filter, Data Actions, Overlay Controls, Playback Control, Merge Sessions, and Data Control.
- On normal laptop/desktop window sizes, those vertical docks were forced to share the same height, so important controls became cramped and hard to read.
- Similar stacking existed on the Preprocess, Train, Validation, and Export pages.
- Old saved Qt layout state could restore the cramped arrangement even after changing default layout code, so the layout storage key needed a version bump.

## Files changed
- `piTrainer/piTrainer/pages/dock_page.py`
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
- `piTrainer/piTrainer/ui/layout_widgets.py`
- `piTrainer/piTrainer/ui/styles.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_1.md`

## Exact behaviour changed
- Added reusable layout widgets:
  - `CollapsibleSection`
  - `ControlStack`
  - `make_scroll_area`
- Data page now uses a single scrollable `Workflow Controls` dock instead of seven cramped left-side docks.
- Data page collapsible sections:
  - Session Source: expanded by default
  - Dataset Stats: expanded by default
  - Frame Filter: collapsed by default
  - Data Actions: expanded by default
  - Overlay Controls: collapsed by default
  - Playback Control: collapsed by default
  - Merge Sessions: collapsed by default
  - Data Control: collapsed by default
- Data page major content is repositioned as:
  - left: scrollable Workflow Controls
  - centre: Record Preview
  - right: Image Preview + V7 Overlay
  - bottom/under record preview: Data Plot
- Preprocess page now uses a scrollable `Preprocess Workflow` sidebar with collapsible Source Summary, Filters, Recipe, and Actions.
- Train page now uses a scrollable `Training Workflow` sidebar and gives more space to Epoch Frame Review.
- Train History and Training Log are tabified so the page is not vertically squeezed.
- Validation page now uses a scrollable `Validation Workflow` sidebar and gives more space to Validation Frame Review.
- Validation Plot and Validation Log are tabified so the user can switch between them without compressing the frame review.
- Export page now uses a scrollable `Export Workflow` sidebar with the log as the main right-side panel.
- Layout persistence was versioned to `0_4_1_readable_scroll_layout` so old saved cramped layouts are not silently restored over the new default.
- Added styling for collapsible headers, bodies, workflow sidebars, and vertical scroll bars.

## Compatibility notes
- No PiSD V7 data loading behaviour was removed.
- No PiSD V7 overlay redraw behaviour was removed.
- No model architecture, training dataset format, validation metric, export artifact, or JSONL edit/merge/delete behaviour was changed.
- Docks are still movable, closable, and floatable.
- The user's old layout state is intentionally ignored for this new layout version; after opening the app, the new layout can be saved normally when the app closes.

## Rollback-risk check
- Checked latest patch note `0_4_0` and previous relevant notes `0_3_20`, `0_3_18`, and `0_3_17`.
- Preserved PiSD V7 `labels.jsonl` / `records.jsonl` support and overlay redraw from `0_4_0`.
- Preserved the optimized PiSD session loading and image-cache work from `0_3_20`.
- Reworked, rather than removed, the dock organisation from `0_3_18`.
- Did not restore the older quarter-ellipse-only overlay behaviour from `0_3_17`; the legacy overlay remains optional/debug only from `0_4_0`.

## Verification actually performed
- Ran `python3 -m compileall -q main.py piTrainer` successfully after the patch.
- Compared the patch against the `piTrainer_0_4_0` applied state and confirmed only the intended layout/style files plus patch notes were changed.
- Checked the patch zip contents to ensure it contains only changed/new files and preserves the exact `piTrainer/...` folder structure.

## Verification not performed
- Full PySide6 GUI smoke rendering was not run in this container because PySide6 is not installed here.
- Full TensorFlow training/validation was not run because this patch only changes layout and dock presentation.

## Known limits / next steps
- On the Windows PC, open each tab and use `Ctrl+Shift+R` once if any old saved geometry still appears unusual.
- If a specific panel still feels too large/small after real monitor testing, the next patch can tune default dock sizes without changing the data/overlay logic.
