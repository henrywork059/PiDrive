# PATCH NOTES — piTrainer_0_5_2 Unified Presentation Format

## Request summary
- Make the styles and formatting of all piTrainer tabs and panels uniform.
- Move presentation values into one shared format system rather than spreading style, spacing, panel width, splitter, and density rules across many files.
- Keep the accepted V5.1 functionality and responsive full-width layout.

## Cause / root cause
V5.1 improved responsive behaviour, but presentation rules were still partly split between:
- `ui/styles.py` density profiles;
- `ui/layout_widgets.py` margins and collapsible-section spacing;
- `pages/dock_page.py` page-shell and splitter-panel spacing;
- individual page splitter sizes and minimums;
- widget-specific roles that were not applied consistently to all tabs/panels.

This made the UI harder to tune because changing the programme's visual format could require editing several unrelated files.

## Files changed
- `piTrainer/piTrainer/ui/formatting.py`  
  New central format source for density profiles, layout metrics, splitter presets, panel minimums, form spacing, widget-role formatting, and whole-window formatting pass.
- `piTrainer/piTrainer/ui/styles.py`  
  Now reads density/style tokens from `ui/formatting.py` instead of keeping separate hard-coded profile values.
- `piTrainer/piTrainer/ui/layout_widgets.py`  
  Collapsible sections, workflow stacks, page banners, and form layouts now use central metrics from `ui/formatting.py`.
- `piTrainer/piTrainer/pages/dock_page.py`  
  Page shell, splitter panel frame, and splitter handle sizing now use the central format system. Layout version bumped to `0_5_2_unified_format`.
- `piTrainer/piTrainer/main_window.py`  
  Responsive density selection and whole-widget formatting now run through the central format system.
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`  
  Page splitter sizes, stretch factors, and minimum panel sizes now use central named presets instead of local per-page number lists.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_5_2.md`

## Exact behaviour changed
- Added one central presentation control file: `piTrainer/piTrainer/ui/formatting.py`.
- Moved compact / comfortable / spacious density settings into the central format file.
- Moved common page, panel, collapsible-section, workflow-stack, form, splitter, and panel-width metrics into the central format file.
- Moved full-width splitter presets into named central presets:
  - `three_panel_workspace`
  - `two_panel_workspace`
  - `preview_over_plot`
  - `preview_over_results`
- Added a whole-program formatting pass that applies consistent roles and behaviour to:
  - tabs;
  - group boxes;
  - normal buttons;
  - next-step buttons;
  - tables;
  - list widgets;
  - wrapped labels;
  - known page/panel layouts.
- Added style rules for centrally tagged content tabs, form groups, and workflow scroll areas.
- Bumped the layout version to `0_5_2_unified_format` so old saved V5.1 sizes do not override the new unified format.

## Preserved behaviour
- All V5.1 responsive sizing improvements are preserved.
- All V5.0 accepted changes are preserved.
- PiSD V7 `labels.jsonl` / `records.jsonl` support is preserved.
- PiSD V7 overlay redraw is preserved.
- Preprocessing/manual-drive fixes are preserved.
- Training-start checks are preserved.
- Green, full-width, subtle-pulse Next Step buttons are preserved.
- Full-width left/middle/right splitter layout is preserved.

## Rollback-risk check
- Checked the latest current code state from V5.1.
- Checked latest patch notes `0_5_1`, `0_5_0`, and `0_4_10` before patching.
- This patch only changes presentation/layout formatting infrastructure and page layout presets.
- It does not restore older dock layouts.
- It does not remove V7 data/overlay support, preprocessing fixes, training fixes, validation logic, or export logic.

## Verification actually performed
- Built forward from `piTrainer_0_5_1_full.zip`.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Checked the patch diff against V5.1.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox because PySide6 is not installed here.
- Full TensorFlow training was not run because this patch changes presentation formatting only.

## Known limits / next steps
- If you want a different visual density, tune the `DENSITY_PROFILES` values in `ui/formatting.py` instead of editing many panel files.
- If you want different default page proportions, tune the `SPLITTER_PRESETS` values in `ui/formatting.py`.
