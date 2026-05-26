# PATCH NOTES — piTrainer_0_6_13 Simple Record Preview Table Rework Patch

## Request summary
- Rework the Record Preview table/list because it still sometimes jumps horizontally to the second column.
- Use a simple and reliable table approach, with online reference method checked.
- Keep `frame_id` as the first column.
- Make the table behaviour simpler and less bug-prone.

## Cause / root cause
Earlier fixes tried to control a `QTableWidget` after selection changes by forcing the current cell back to column 1 and repeatedly resetting the horizontal scrollbar. That reduced the issue but did not remove the root cause: the item-based table still kept per-cell current selection state. During multi-row selection, click selection, select-all, resize, or delayed row updates, Qt could still treat a later cell as the current cell and scroll horizontally to make that later cell visible.

The table was also carrying more metadata columns than most users need during frame review. More columns increase the chance that horizontal scrolling becomes visible and confusing.

## Online reference method checked
- Qt's model/view documentation describes separating the view from the data model for table widgets.
- Qt's `QTableView` documentation describes `QTableView` as the standard table view for the model/view framework.
- Based on that method, this patch replaces the Record Preview implementation with a small read-only `QTableView` + `QAbstractTableModel` instead of fighting `QTableWidget` current-cell behaviour.

## Files changed
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Replaces the item-based `QTableWidget` Record Preview implementation with:
    - `RecordPreviewModel`, a small read-only `QAbstractTableModel`;
    - `CyclingPreviewTable`, a `QTableView` subclass that preserves Up/Down cycling.
  - Keeps row selection direct and simple: view row equals preview dataframe row because sorting is disabled.
  - Keeps `frame_id` as the first visible column.
  - Keeps multi-row selection, Select All Visible Frames, Delete/Hide integration, playback, and targeted visible-row updates.
  - Keeps horizontal first-column anchoring without forcing normal mouse selections into the vertical centre.
- `piTrainer/piTrainer/services/data/preview_service.py`
  - Simplifies the visible Record Preview columns to a stable short order:
    - `frame_id`, `session`, `steering`, `throttle`, `mode`, `ts`.
  - Ensures `frame_id` is always first when present.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_13_simple_record_preview_model`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.13` / `piTrainer_0_6_13`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the accepted Record Preview table pattern.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions to preserve the simple model/view Record Preview approach.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_13.md`
  - This patch note.

## Exact behaviour changed
- Record Preview now uses a read-only model/view table instead of a cell-item table.
- Table sorting is disabled to keep row mapping simple and predictable.
- The visible Record Preview columns are shorter and stable.
- `frame_id` remains the first visible column.
- Selection maps directly to the active preview dataframe row.
- Multi-select and Select All should be more stable because the table no longer depends on storing source row mapping in individual cell items.
- Horizontal anchoring still resets the scrollbar to the first column after selection/current-index changes.
- Normal mouse selection still does not force the selected row into the vertical centre.

## Behaviour intentionally not changed
- Data Workflow tab order remains `1 Load`, `2 Manage`, `3 Review`.
- Data Review tab order remains `1 Records`, `2 Stats`, `3 Plot`.
- Playback controls remain under Image Preview.
- Up/Down arrow keys still cycle through Record Preview rows.
- Bulk Edit Selected Frames remains in `3 Review` and still supports Select All Visible Frames.
- Bulk edits still apply only one field at a time and still use the batch JSONL updater.
- Soft-delete/hide remains traceable and hidden rows remain excluded from preprocessing, training, and validation.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading and overlay redraw support are unchanged.
- Queued/debounced Image Preview edits from 0.6.12 are preserved.
- Preprocess auto workflow and training GPU device controls are unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.12` install.
- Existing PiSD sessions do not need migration.
- Existing saved layouts may reset because `FORMAT_VERSION` changed for the Record Preview table implementation.
- The full underlying dataframe is still kept internally; this patch only simplifies what the Record Preview table displays.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_12` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_12.md`
  - `PATCH_NOTES_piTrainer_0_6_11.md`
  - `PATCH_NOTES_piTrainer_0_6_10.md`
  - `PATCH_NOTES_piTrainer_0_6_9.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support;
  - PiSD V7 overlay redraw support;
  - preprocessing/manual-drive fixes;
  - training-start preflight fixes;
  - full-width splitter layout;
  - horizontal overflow scroll behaviour;
  - V6.1 playback-under-preview layout;
  - V6.2 Data Workflow and Data Review tab orders;
  - V6.2 AI-agent instruction document;
  - V6.3 Data Control checkbox and multi-row Record Preview selection;
  - V6.4 label cleanup and first-column anchoring intent;
  - V6.5 central theme token system;
  - V6.6 amber/green action colour semantics and centred steering slider;
  - V6.7 Bulk Edit Selected Frames panel and edit safety;
  - V6.8 traceable soft-delete / hidden-frame behaviour;
  - V6.9 fast batch JSONL bulk-edit path;
  - V6.10 Up/Down cycling, Bulk Edit Select All, and targeted edit optimisation;
  - V6.11 Preprocess auto workflow and training device/GPU controls;
  - V6.12 validation import fix, TensorFlow log handling, and queued edit responsiveness.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_12_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Record Preview panel, preview service, Data page usage, latest patch notes, style guide, and AI-agent instructions.
- Checked online Qt documentation for the model/view table approach.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.13`;
  - `PATCH_VERSION` reports `piTrainer_0_6_13`;
  - `FORMAT_VERSION` reports `0_6_13_simple_record_preview_model`;
  - `preview_panel.py` now uses `QTableView` / `QAbstractTableModel`;
  - `preview_panel.py` no longer uses `QTableWidget` / `QTableWidgetItem`;
  - `preview_service.py` keeps `frame_id` first in `PREVIEW_COLUMN_ORDER`.
- Compared the working tree against fresh V6+0.6.1 through 0.6.12 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Direct PySide6 import/smoke testing was not possible because this sandbox does not have PySide6 installed.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow validation/training was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- The table intentionally has fewer visible metadata columns. If a future workflow needs advanced metadata inspection, it should go into a separate advanced/detail panel rather than widening the main Record Preview table again.
- If live testing still finds a horizontal jump, the next step should be to lock horizontal scrolling completely for this compact table rather than reintroducing item-based table logic.
