# PATCH NOTES — piTrainer_0_6_2 Data Workflow Reorder and Agent Instructions Patch

## Request summary
- Include an AI agent instruction document for future piTrainer work.
- Make Browse buttons amber so folder-selection actions stand out from normal secondary buttons.
- Reorder the central Data Review tabs to `1 Records`, `2 Stats`, `3 Plot`.
- Reorder the left Data Workflow tabs to `1 Load`, `2 Manage`, `3 Review`.
- Keep Data Control expanded by default.
- Move Merge Sessions into the Review workflow.
- Allow deleting the selected frame with the keyboard `Delete` key.

## Cause / root cause
The V6.1 layout had the right high-level direction, but some task ordering and action placement still did not match the user's preferred workflow:

- Central review opened on stats before records, even though selecting a record drives preview, playback, editing, and deletion.
- The left workflow order still presented Review before Manage.
- Merge Sessions was grouped under Manage, but the user wanted it available from Review.
- Browse buttons looked like ordinary secondary actions even though choosing a folder is an important location step.
- Frame deletion required finding the Delete button manually.
- Future AI handoff instructions existed in chat prompts but not yet as a repo file.

## Files changed
- `piTrainer/AGENTS.md`
  - New AI-agent instruction document for piTrainer continuation work.
  - Records component scope, V6 baseline, 0_6_x patch line, anti-rollback rules, V6 behaviours to preserve, UI/layout rules, packaging checklist, and verification wording.
- `piTrainer/piTrainer/pages/data_page.py`
  - Reorders `Data Workflow` to `1 Load`, `2 Manage`, `3 Review`.
  - Keeps `Data Control` expanded by default inside `2 Manage`.
  - Moves `Merge Sessions` into `3 Review`.
  - Reorders `Data Review` to `1 Records`, `2 Stats`, `3 Plot`.
  - Updates Data page banner/helper wording to match the new workflow.
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
  - Updates helper text to mention the `Delete` keyboard shortcut.
- `piTrainer/piTrainer/panels/data/session_source_panel.py`
  - Marks the records-root Browse button with the shared `amber` role.
- `piTrainer/piTrainer/panels/data/root_path_panel.py`
  - Marks the older records-root Browse button with the shared `amber` role for consistency if it is reused.
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
  - Marks the output-directory Browse button with the shared `amber` role for consistency.
- `piTrainer/piTrainer/main_window.py`
  - Adds `Delete` as a Data-page shortcut for deleting the selected frame after confirmation.
  - Adds the shortcut to the F1 shortcut list.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_2_workflow_reorder_delete_shortcut` so older saved layout states do not override the new default tab order.
  - Adds `amber` to the known button role set.
- `piTrainer/piTrainer/ui/styles.py`
  - Adds amber button styling for Browse/location-picking buttons.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.6.2` / `piTrainer_0_6_2`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Updates the documented Data Workflow and Data Review tab orders.
  - Documents the amber Browse button role.
  - Documents that Data Control remains expanded by default by user request.
  - Adds guidance to keep `AGENTS.md` aligned with future workflow-rule changes.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_2.md`
  - This patch note.

## Exact behaviour changed
- The left Data Workflow panel now presents:
  - `1 Load`
  - `2 Manage`
  - `3 Review`
- `2 Manage` contains `Data Control` and is expanded by default.
- `3 Review` now contains:
  - `Merge Sessions`
  - `Frame Filter`
  - `Overlay Controls`
- The central Data Review panel now presents:
  - `1 Records`
  - `2 Stats`
  - `3 Plot`
- Browse buttons now use an amber role instead of normal secondary styling.
- Pressing `Delete` while the Data page is active calls the same confirmed delete flow as the `Delete Selected Frame` button.
- The F1 shortcut dialog now lists the Delete shortcut.
- The app window/status version now reports `0.6.2`.
- A new `piTrainer/AGENTS.md` file is included for future AI coding-agent handoff.

## Behaviour intentionally not changed
- The confirmed deletion behaviour is still used; the keyboard shortcut does not silently delete frames.
- `Delete Selected Frame` still updates both `labels.jsonl` and `records.jsonl` through the existing delete service where available.
- Playback controls remain directly under the image preview from V6.1.
- Dataset stats remain inside `Data Review` from V6.1, but are now the second tab.
- The old generic `Data Actions` panel is still not used in the active Data page layout.
- Refresh/load remain in `Session Source`.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and overlay metadata support are unchanged.
- Preprocess, Train, Validate, and Export workflow logic is unchanged, except for the Export Browse button visual role.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6/V6.1 install.
- `FORMAT_VERSION` was bumped so the new default Data page arrangement is not hidden by older saved splitter/tab layout state.
- The keyboard delete shortcut still shows the existing confirmation dialog before removing anything.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with the accepted `piTrainer_0_6_1_patch` applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_1.md`
  - `PATCH_NOTES_piTrainer_0_6_0.md`
  - `PATCH_NOTES_piTrainer_0_5_7.md`
  - `PATCH_NOTES_piTrainer_0_5_6.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support.
  - PiSD V7 overlay redraw support.
  - Preprocessing/manual-drive fixes.
  - Training-start preflight fixes.
  - Full-width splitter layout.
  - Horizontal overflow scroll behaviour.
  - Compact guided banner.
  - Green Next Step buttons.
  - Central formatting/style system.
  - V6.1 playback-under-preview layout.
  - V6.1 stats-inside-Data-Review layout.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the Data page, shortcut registration, style/format files, and latest patch notes.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Confirmed changed source text contains:
  - `Data Workflow`: `1 Load`, `2 Manage`, `3 Review`.
  - `Data Review`: `1 Records`, `2 Stats`, `3 Plot`.
  - `QShortcut(QKeySequence('Delete'), self.data_page, activated=self.data_page.delete_selected_frame)`.
  - Browse buttons marked with `role='amber'`.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch changes Data page presentation, shortcut binding, documentation, and button styling only.

## Known limits / next steps
- If the user wants Delete to work only when the Records table itself has focus, the shortcut can be moved from the Data page to the table widget in a future patch.
- If further Browse buttons are added in new panels, they should use the `amber` role.
