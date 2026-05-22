# PATCH NOTES — piTrainer_0_6_4 Record Table First-Column and Action Label Cleanup Patch

## Request summary
- Fix Record Preview behaviour where multi-frame selection could leave the table horizontally shifted so the first column was not visible.
- Remove the old visible label prefixes `Next Step:` and `Show:` from the guided action buttons.

## Cause / root cause
The V6.3 Record Preview table correctly allowed multi-row selection, but Qt could keep the horizontal scroll position near the cell used during selection. When users selected several rows from a later column, the table could stay horizontally shifted and appear to begin at the second column instead of the first `frame_id` column.

The guided UI also still used older wording from the V5 compact banner work:
- green action buttons were labelled with `Next Step:`;
- compact banner guide buttons were labelled with `Show:`.

The user requested simpler labels without those words.

## Files changed
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Adds a small first-column visibility guard after table selection changes.
  - Keeps the horizontal scrollbar anchored to the first column after row/multi-row selection.
  - Preserves multi-row selection and current-row image preview behaviour.
  - Changes preview summary text from `Showing` to `Displaying`.
- `piTrainer/piTrainer/pages/data_page.py`
  - Changes the Data banner guide label from `Show: Load Selected` to `Load Selected`.
  - Changes guide status/tooltip wording from show wording to focus wording.
  - Changes preview status text to `Displaying ... preview frame(s)`.
  - Updates delete-checkbox wording to avoid repeated popup wording using show.
- `piTrainer/piTrainer/pages/preprocess_page.py`
  - Changes the banner guide label from `Show: Confirm Preprocess` to `Confirm Preprocess`.
  - Updates guide status/tooltip wording.
- `piTrainer/piTrainer/pages/train_page.py`
  - Changes the banner guide label from `Show: Start Training` to `Start Training`.
  - Updates guide status/tooltip wording.
- `piTrainer/piTrainer/pages/validation_page.py`
  - Changes the banner guide label from `Show: Run Validation` to `Run Validation`.
  - Updates guide status/tooltip wording.
- `piTrainer/piTrainer/pages/export_page.py`
  - Changes the banner guide label from `Show: Export Artifacts` to `Export Artifacts`.
  - Updates guide status/tooltip wording.
- `piTrainer/piTrainer/panels/data/session_source_panel.py`
  - Changes the green button label from `Next Step: Load Selected` to `Load Selected`.
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
  - Changes the green button label from `Next Step: Confirm and Start Preprocess` to `Confirm and Start Preprocess`.
- `piTrainer/piTrainer/panels/train/train_control_panel.py`
  - Changes the green button label from `Next Step: Start Training` to `Start Training`.
- `piTrainer/piTrainer/panels/validation/validation_actions_panel.py`
  - Changes the green button label from `Next Step: Run Validation` to `Run Validation`.
- `piTrainer/piTrainer/panels/export/export_actions_panel.py`
  - Changes the green button label from `Next Step: Export Selected Artifacts` to `Export Selected Artifacts`.
- `piTrainer/piTrainer/panels/data/data_actions_panel.py`
  - Cleans the inactive legacy panel labels as a safety measure in case it is ever inspected or reused.
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
  - Updates helper wording from repeated confirmation display wording to popup-open wording.
- `piTrainer/piTrainer/panels/data/overlay_control_panel.py`
  - Changes overlay checkbox labels from `Show ...` to `Display ...`.
- `piTrainer/piTrainer/panels/data/playback_control_panel.py`
  - Changes helper wording from shown to displayed.
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
  - Changes `Show only bad predictions` to `Only bad predictions`.
- `piTrainer/piTrainer/ui/layout_widgets.py`
  - Updates default guide/action wording and helper comments.
- `piTrainer/piTrainer/pages/dock_page.py`
  - Updates reveal helper comments to refer to green action buttons.
- `piTrainer/piTrainer/main_window.py`
  - Updates the startup status wording and F1 shortcut description.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_4_record_table_first_column_action_labels`.
- `piTrainer/piTrainer/version.py`
  - Updates visible version metadata to `0.6.4` / `piTrainer_0_6_4`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents first-column anchoring for multi-row Record Preview selection.
  - Documents the new simpler action-label rule.
- `piTrainer/AGENTS.md`
  - Updates future-agent guidance for first-column anchoring and label prefixes.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_4.md`
  - This patch note.

## Exact behaviour changed
- Multi-row selection in Record Preview should keep the table scrolled back to the first visible column, so `frame_id` remains visible.
- Green workflow action buttons now use action names only:
  - `Load Selected`
  - `Confirm and Start Preprocess`
  - `Start Training`
  - `Run Validation`
  - `Export Selected Artifacts`
- Compact page banner guide buttons now use action names only:
  - `Load Selected`
  - `Confirm Preprocess`
  - `Start Training`
  - `Run Validation`
  - `Export Artifacts`
- User-facing labels that previously used show wording in the touched panels now use display/open/focus wording instead.
- The app window/status version now reports `0.6.4`.

## Behaviour intentionally not changed
- Data Workflow remains ordered as `1 Load`, `2 Manage`, `3 Review`.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot`.
- Frame Filter remains in `2 Manage`.
- Merge Sessions remains in `3 Review` and collapsed by default.
- Data Control remains expanded by default.
- The delete checkbox flow from V6.3 remains unchanged.
- Record Preview still supports multi-row selection and batch deletion.
- `frame_id` remains the first Record Preview column.
- Playback controls remain directly under the image preview.
- Browse buttons keep the more yellowish amber styling from V6.3.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and overlay metadata support are unchanged.
- Preprocess, Train, Validate, and Export runtime logic is unchanged apart from button/guide label wording.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + 0.6.1 + 0.6.2 + 0.6.3 install.
- `FORMAT_VERSION` was bumped so old saved layout state is less likely to preserve outdated UI arrangement/labels.
- The first-column guard only adjusts horizontal table scroll position; it does not change the selected rows or the selected preview record.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1`, `0_6_2`, and `0_6_3` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_3.md`
  - `PATCH_NOTES_piTrainer_0_6_2.md`
  - `PATCH_NOTES_piTrainer_0_6_1.md`
  - `PATCH_NOTES_piTrainer_0_6_0.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support.
  - PiSD V7 overlay redraw support.
  - Preprocessing/manual-drive fixes.
  - Training-start preflight fixes.
  - Full-width splitter layout.
  - Horizontal overflow scroll behaviour.
  - V6.1 playback-under-preview layout.
  - V6.2 Data Workflow and Data Review tab orders.
  - V6.2 AI-agent instruction document.
  - V6.3 Data Control delete checkbox.
  - V6.3 multi-row selection and batch delete support.
  - V6.3 `frame_id` first-column order.
  - V6.3 yellowish amber browse button styling.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip`, `piTrainer_0_6_2_patch.zip`, and `piTrainer_0_6_3_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the Data page, Record Preview panel, page banner helper, green action button labels, style guide, agent instructions, and latest patch notes.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.4`.
  - `FORMAT_VERSION` reports `0_6_4_record_table_first_column_action_labels`.
  - Green action button labels no longer include `Next Step:`.
  - Page banner guide labels no longer include `Show:`.
  - Record Preview has `_keep_first_column_visible()` and schedules it after selection changes.
  - `frame_id` is still first in the preview service column order.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3 to identify only intended changed files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch changes table selection display behaviour and UI wording only.

## Known limits / next steps
- The first-column guard is designed for the Record Preview table. If future tables gain similar multi-row selection behaviour, the same pattern can be shared as a helper.
