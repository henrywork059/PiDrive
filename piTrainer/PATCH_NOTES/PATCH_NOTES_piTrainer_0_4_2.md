# PATCH NOTES — piTrainer_0_4_2

## Request summary
- Continue the `0_4_1` readability redesign.
- Apply collapsible and scrollable layout patterns to more panels and tabs.
- Reduce remaining cramped controls without removing PiSD V7 data or overlay support.

## Cause / root cause
- `0_4_1` fixed the biggest dock-stacking issue by replacing many separate side docks with scrollable workflow sidebars.
- After that first pass, some workflow sidebars were still long, especially the Data, Preprocess, Train, Validation, and Export pages.
- Several individual panels were still dense internally: Training Config, Preprocess Filters, Preprocess Recipe, Validation Config, Export Options, Data Plot controls, Image Preview edit controls, and Validation Frame Review filters.
- The result was better than before, but still too much content could be visible at once on smaller screens.

## Files changed
- `piTrainer/piTrainer/pages/dock_page.py`
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
- `piTrainer/piTrainer/panels/data/data_plot_panel.py`
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_config_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_filter_panel.py`
- `piTrainer/piTrainer/panels/train/train_config_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_config_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/piTrainer/ui/layout_widgets.py`
- `piTrainer/piTrainer/ui/styles.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_2.md`

## Exact behaviour changed
- Added reusable workflow helpers:
  - `make_workflow_tabs()` for task-family tabs inside a workflow dock.
  - `make_scrollable_stack()` for shorter creation of scrollable collapsible stacks.
- Data page workflow is now tabbed:
  - `Load`: Session Source, Dataset Stats, Data Actions.
  - `Review`: Frame Filter, Overlay Controls, Playback Control.
  - `Manage`: Merge Sessions, Data Control.
- Preprocess page workflow is now tabbed:
  - `Source`: Source Summary and Preprocess Filters.
  - `Recipe`: Preprocess Recipe and Preprocess Actions.
- Train page workflow is now tabbed:
  - `Setup`: Split Summary and Training Controls.
  - `Config`: Training Config.
- Validation page workflow is now tabbed:
  - `Run`: Validation Config and Validation Actions.
  - `Status`: Validation Summary.
- Export page workflow is now tabbed:
  - `Status`: Model Status.
  - `Export`: Export Options and Export Actions.
- Training Config is now divided into collapsible internal groups:
  - Input Size + Split.
  - Model + Loss.
  - Training Schedule.
  - Review + Dataset Options.
- Preprocess Filters is now divided into collapsible internal groups:
  - Source + Mode.
  - Frame Thinning.
  - Steering + Speed Ranges.
  - Straight-row Balancing.
- Preprocess Recipe is now divided into collapsible internal groups:
  - Turning Boost.
  - Mirror + Color Variants.
  - Output Image Size.
- Validation Config is now divided into collapsible internal groups:
  - Model Source.
  - Dataset + Run Limits.
- Export Options is now divided into collapsible internal groups:
  - Destination.
  - Artifact Types.
- Data Plot now collapses plot controls and summary so the chart gets more vertical space.
- Image Preview now collapses the steering/speed editor and overlay metadata so the image gets more vertical space.
- Validation Frame Review now collapses filter/sort controls so the table and image preview get more room.
- Layout persistence was versioned to `0_4_2_tabbed_collapsible_layout` so old cramped saved layouts from `0_4_1` do not override the new default.
- Styling now applies to all scroll areas and the new workflow tabs, not only the first-generation `0_4_1` scroll-area object names.

## Compatibility notes
- No PiSD V7 `labels.jsonl` / `records.jsonl` loader behaviour was changed.
- No PiSD V7 overlay metadata or overlay redraw behaviour was removed.
- No training model architecture, preprocessing formula, validation metric, or export artifact logic was changed.
- Existing shortcuts and dock save/restore behaviour remain in place, with a new layout version key.
- The user's old custom layout is intentionally bypassed once so the less-cramped default can load.

## Rollback-risk check
- Checked latest patch notes `0_4_1`, `0_4_0`, `0_3_20`, and `0_3_18` before finalizing.
- Preserved the `0_4_1` scrollable workflow dock concept and extended it rather than reverting to separate stacked docks.
- Preserved the `0_4_0` PiSD V7 overlay redraw and data compatibility work.
- Preserved the `0_3_20` PiSD session discovery / `labels.jsonl` optimisation work.
- Preserved the `0_3_18` dock-oriented page architecture while improving the default content grouping.

## Verification actually performed
- Ran `python3 -m compileall -q main.py piTrainer` successfully after the patch.
- Compared the changed file list against the `0_4_1` applied state and confirmed only layout/panel presentation files plus patch notes were changed.
- Checked the patch package contents to ensure it contains only changed/new files and preserves the exact `piTrainer/...` folder structure.

## Verification not performed
- Full PySide6 GUI rendering was not run in this container because PySide6 is not installed here.
- Full TensorFlow training/validation was not run because this patch only changes UI layout and panel presentation.

## Known limits / next steps
- On the Windows PC, open each tab and use `Ctrl+Shift+R` once if the new layout does not appear immediately.
- If a real monitor test shows one tab should be open by default instead of collapsed, the next patch can tune default expanded/collapsed states without touching PiSD V7 data logic.
