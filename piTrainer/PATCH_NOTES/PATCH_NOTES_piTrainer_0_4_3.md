# PATCH NOTES — piTrainer_0_4_3

## Request summary
- Review the presentation/readability of the whole piTrainer program.
- Compare the current layout method against online UI/Qt references.
- Improve and optimise the interface so it is more user friendly and easier to read across all pages.
- Build forward from `piTrainer_0_4_2` without rolling back PiSD V7 data or overlay compatibility.

## Design basis / online reference comparison
- Qt `QDockWidget` remains appropriate for large movable/floating work areas, but too many small docks create cramped panes. This patch keeps dockable work areas but makes the workflow sidebars more guided and less memory-dependent.
- Qt `QScrollArea` is appropriate for dense control sidebars because it lets content remain reachable when the visible area is smaller than the controls.
- Qt `QFormLayout` is appropriate for labelled configuration forms. The patch standardises label alignment, row wrapping, and field growth so long labels do not crush input fields.
- GNOME HIG adaptive guidance warns that windows subdivided into numerous small panes are hard to make adaptive. The patch continues reducing tiny panes by using task tabs, scrollable sidebars, and larger primary review areas.
- Nielsen Norman Group usability heuristics support keeping system status visible, using user-language labels, consistency, recognition rather than recall, and aesthetic/minimalist design. The patch adds clearer workflow names, numbered top-level tabs, helper text, primary/secondary/danger button roles, and less visual noise.

## Cause / root cause
- `0_4_1` and `0_4_2` fixed the worst panel-clamping problem with scrollable/collapsible/tabbed workflow sidebars.
- The programme was still inconsistent in smaller ways:
  - top-level tabs did not communicate the end-to-end workflow order;
  - workflow sidebar tabs had short labels but little instruction;
  - buttons all looked similar, so destructive, primary, and secondary actions were not visually distinct;
  - dense forms used slightly different spacing/label wrapping rules;
  - record/validation tables did not consistently use alternating rows, hidden vertical headers, or improved column behaviour;
  - log/preview text panels lacked helpful placeholders and line wrapping.

## Files changed
- `piTrainer/piTrainer/main_window.py`
- `piTrainer/piTrainer/pages/dock_page.py`
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
- `piTrainer/piTrainer/ui/layout_widgets.py`
- `piTrainer/piTrainer/ui/styles.py`
- `piTrainer/piTrainer/panels/common/log_panel.py`
- `piTrainer/piTrainer/panels/data/data_actions_panel.py`
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
- `piTrainer/piTrainer/panels/data/dataset_stats_panel.py`
- `piTrainer/piTrainer/panels/data/frame_filter_panel.py`
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
- `piTrainer/piTrainer/panels/data/merge_sessions_panel.py`
- `piTrainer/piTrainer/panels/data/playback_control_panel.py`
- `piTrainer/piTrainer/panels/data/preview_panel.py`
- `piTrainer/piTrainer/panels/data/session_source_panel.py`
- `piTrainer/piTrainer/panels/export/export_actions_panel.py`
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
- `piTrainer/piTrainer/panels/export/model_status_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_config_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_filter_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_result_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_summary_panel.py`
- `piTrainer/piTrainer/panels/train/split_summary_panel.py`
- `piTrainer/piTrainer/panels/train/train_config_panel.py`
- `piTrainer/piTrainer/panels/train/train_control_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_actions_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_config_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_summary_panel.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_3.md`

## Exact behaviour changed
- Top-level tabs are now numbered by workflow order:
  - `1 Data`
  - `2 Preprocess`
  - `3 Train`
  - `4 Validate`
  - `5 Export`
- The main window title and ready/status message now describe the actual trainer workflow.
- Top-level tabs now have tooltips explaining each page's purpose.
- Workflow sidebar tabs are now numbered and include concise intro cards explaining what to do in that tab.
- The layout persistence version was bumped to `0_4_3_guided_readable_layout` so old `0_4_2` saved layouts do not override the improved defaults.
- Reusable UI helpers were expanded:
  - `make_hint_label()` for consistent readable helper text.
  - `standardize_form_layout()` for consistent form spacing, label alignment, field growth, and long-row wrapping.
  - workflow tab helpers now support tab tooltips and avoid horizontal scrollbar clutter in workflow sidebars.
- Button presentation is now clearer:
  - primary actions such as Load Selected, Confirm Preprocess, Start Training, Run Validation, Export, and Edit in Data are visually highlighted;
  - secondary actions such as Browse, Refresh, Preview, Reset, Clear, Save Settings, and playback helpers are quieter;
  - destructive actions such as Delete Selected Frame and Stop are visually separated.
- Record Preview table readability improved:
  - alternating rows;
  - hidden vertical row header;
  - larger minimum height;
  - interactive column widths;
  - resize-to-content after loading rows;
  - word wrapping disabled in cells to avoid tall unreadable rows.
- Validation Frame Review table received the same readability treatment.
- Image Preview now gives the image more vertical space and uses clearer wording that editing is optional.
- Dense forms across Data, Preprocess, Train, Validation, and Export now use consistent form layout behaviour.
- Logs and preprocess preview text now have placeholders and wrap to panel width.
- Summary labels in Preprocess and Validation can be selected/copied more easily.
- Styling was polished programme-wide:
  - slightly larger base text;
  - more spacing around controls;
  - clearer dock titles;
  - stronger focus outlines;
  - more readable tables and scrollbars;
  - consistent card-like helper text;
  - clearer visual hierarchy between page tabs, workflow tabs, sections, forms, and actions.

## Compatibility notes
- No PiSD V7 `labels.jsonl` / `records.jsonl` loader behaviour was changed.
- No PiSD V7 overlay metadata or overlay redraw behaviour was removed.
- No preprocessing formulas, training model architecture, validation metrics, or export artefact logic was changed.
- Existing keyboard shortcuts remain in place; only the shortcut text was updated to match the new numbered tabs.
- The old custom layout is intentionally bypassed once because the saved layout version changed.

## Rollback-risk check
- Checked recent patch notes `0_4_2`, `0_4_1`, `0_4_0`, and `0_3_20` before finalizing.
- Preserved the `0_4_2` tabbed/collapsible workflow structure and extended it with stronger guidance and consistency.
- Preserved the `0_4_1` scrollable workflow sidebar pattern.
- Preserved the `0_4_0` PiSD V7 overlay/data compatibility work.
- Preserved the `0_3_20` session discovery / `labels.jsonl` optimisation work.
- No older file copy was restored over the current accepted state.

## Verification actually performed
- Ran `python3 -m compileall -q main.py piTrainer` successfully after the patch.
- Compared changed files against the `0_4_2` applied state.
- Checked that only presentation/layout/panel files and patch notes changed.
- Removed generated `__pycache__` folders before packaging.
- Packaged only changed/new files, preserving exact `piTrainer/...` folder structure.

## Verification not performed
- Full PySide6 GUI rendering was not run in this container because PySide6 is not installed here.
- Full TensorFlow training/validation was not run because this patch only changes UI presentation and layout.

## Known limits / next steps
- On the Windows PC, open each page and press `Ctrl+Shift+R` once if any old saved layout still appears.
- If the Data page image preview still needs more space on the actual monitor, the next patch can make Image Preview the central/default-largest work area without touching data loading or overlay logic.
