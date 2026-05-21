# PATCH NOTES — piTrainer_0_4_10

## Request summary
- Review and improve the presentation of piTrainer across the whole programme.
- Compare the current layout method with online UI/Qt references.
- Enhance layout, style, and formatting so the trainer is more user-friendly and easier to read.
- Preserve the accepted full-width splitter layout, green next-step buttons, PiSD V7 data/overlay support, and preprocessing/training fixes.

## Online/reference comparison used
- Qt `QSplitter` guidance: splitters are suitable when users need to drag boundaries to control child-widget sizes. This supports keeping the 0_4_7 full-width splitter direction instead of returning to dock panels.
- Qt `QScrollArea` guidance: scroll areas are appropriate for content that can exceed the visible frame. This supports keeping dense workflow controls in scrollable sidebars.
- GNOME/adaptive UI guidance: windows split into too many small panes are harder to scale and read. This supports using progressive disclosure, workflow tabs, page banners, and clearer panel hierarchy rather than showing every control at once.
- GNOME/layout guidance: consistent spacing, grouping, and top-left-to-bottom-right reading order improve visual flow. This supports stronger page headers, consistent padding, and clearer summary cards.

## Cause / design issue
- Earlier patches fixed the main crowding problem, but pages still relied heavily on the user already knowing the workflow.
- Users could see many panels but not always immediately know:
  - what the current stage is;
  - what to check first;
  - what the next action is;
  - which text is status/output versus detailed settings.
- Some summary values looked like normal labels, so important counts/statuses were not visually distinct enough.

## Files changed
- `piTrainer/piTrainer/main_window.py`
- `piTrainer/piTrainer/pages/dock_page.py`
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
- `piTrainer/piTrainer/panels/data/dataset_stats_panel.py`
- `piTrainer/piTrainer/panels/export/model_status_panel.py`
- `piTrainer/piTrainer/panels/train/split_summary_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_summary_panel.py`
- `piTrainer/piTrainer/ui/layout_widgets.py`
- `piTrainer/piTrainer/ui/styles.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_10.md`

## Exact behaviour changed
- Added a consistent page banner above every main page:
  - step number, e.g. `1 of 5`;
  - page title;
  - short purpose statement;
  - a green next-action hint on the right.
- Bumped the layout version to `0_4_10_presentation_layout` so older saved splitter sizes do not override the improved presentation defaults.
- Improved main tab styling so the five programme stages are easier to read.
- Improved the page shell spacing and border rhythm so content is no longer pressed against the window edge.
- Improved splitter panel framing and titles.
- Increased splitter handle width slightly so the drag handles are easier to find.
- Improved visual hierarchy for workflow intro/help labels.
- Made important numeric/status values appear as small stat cards in:
  - Dataset Stats;
  - Split Summary;
  - Model Status.
- Improved Validation Summary formatting with clearer summary line/block styling.
- Improved Validation Frame Review table readability by enabling:
  - alternating rows;
  - hidden vertical header;
  - non-wrapping cells;
  - interactive column resizing;
  - resize-to-content after refresh.
- Polished table, log, scroll, tab, group, and page-banner styling.
- Updated the initial status message to remind users to follow the green next-step buttons and adjust proportions using splitter handles.

## Preserved behaviour
- PiSD V7 `labels.jsonl` and `records.jsonl` loading was not changed.
- PiSD V7 overlay redraw behaviour was not changed.
- The 0_4_9 PiSD manual-mode preprocessing fix was preserved.
- The 0_4_8 green next-step button behaviour was preserved.
- The 0_4_7 full-width splitter layout behaviour was preserved.
- The 0_4_6 training-start preflight and split refresh logic were preserved.
- The 0_4_5 sorted table / edit-delete fixes were preserved.

## Rollback-risk check
- Checked the latest patch note `0_4_9` and previous three notes `0_4_8`, `0_4_7`, and `0_4_6`.
- Confirmed this patch is presentation/layout-only except for table display settings and label roles.
- Did not restore older page files or remove accepted PiSD V7, preprocessing, training, or overlay fixes.
- Kept the latest full-width splitter and green next-step button design direction.

## Verification actually performed
- Applied the patch forward from the accepted `0_4_9` state.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parse over all Python files.
- Checked changed-file diff against the `0_4_9` state.
- Removed generated `__pycache__` folders before packaging.
- Packaged only changed/new files plus this patch note, preserving exact `piTrainer/...` paths.

## Verification not performed
- A live Windows/PySide6 visual render test was not run inside this sandbox.
- Full TensorFlow training was not run because this patch changes presentation/layout only.

## Known limits / next steps
- If the page banners feel too tall on a very small screen, reduce the banner padding in `piTrainer/ui/styles.py`.
- If the top-level tabs still feel too wide on a narrow screen, reduce the `min-width` in the `QTabWidget#mainWorkflowTabs QTabBar::tab` rule.
