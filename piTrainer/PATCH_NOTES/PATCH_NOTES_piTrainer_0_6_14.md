# PATCH NOTES — piTrainer_0_6_14 Sortable Record Preview Table Patch

## Request summary
- Add a table sort function to the Record Preview table.
- Keep the default sorting by `frame_id`.
- Preserve the simple, stable Record Preview table rework from V6.13.

## Cause / root cause
V6.13 simplified the Record Preview table by moving from `QTableWidget` to a read-only `QTableView` with a small `QAbstractTableModel`. That made the table more stable and kept `frame_id` as the first visible column, but sorting was intentionally disabled to reduce risk while fixing the horizontal column-jump problem.

The user now wants sorting back. To avoid reintroducing the old table bugs, this patch keeps the model/view approach and implements sorting inside the table model with an explicit mapping from sorted view rows back to the original dataframe rows.

## Files changed
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Enables header sorting on the Record Preview `QTableView`.
  - Adds sorting support to `RecordPreviewModel`.
  - Defaults the table to sort by `frame_id` ascending when data is loaded.
  - Adds natural sorting for `frame_id` values so `frame_2` sorts before `frame_10`.
  - Keeps a source-row mapping so selection, image preview, bulk edit, soft-hide/delete, targeted row updates, Up/Down cycling, and playback continue to operate on the correct original dataframe row after sorting.
  - Captures and restores selected source rows across header sort operations where possible.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_14_sortable_record_preview`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.14` / `piTrainer_0_6_14`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the new sortable Record Preview model rule.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions to preserve the sortable model/view table and default `frame_id` sort.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_14.md`
  - This patch note.

## Exact behaviour changed
- Record Preview table headers can now be clicked to sort visible rows.
- The default table order is `frame_id` ascending.
- `frame_id` remains the first visible column.
- Sorting does not depend on `QTableWidget` item state.
- The table model now maps sorted view rows back to original dataframe rows before returning selected records.
- Soft-hide/delete and Bulk Edit still target the correct selected frame records even when the visible table is sorted.
- Existing row selections are preserved across header sort operations where possible, using the source-row mapping.

## Behaviour intentionally not changed
- Record Preview still uses the V6.13 read-only `QTableView` / `QAbstractTableModel` pattern.
- The visible column order remains short and stable:
  - `frame_id`, `session`, `steering`, `throttle`, `mode`, `ts`.
- Horizontal anchoring to the first column is preserved.
- Normal mouse selection still does not force the selected row into the vertical middle of the table.
- Up/Down arrow keys still cycle through visible rows.
- Bulk Edit Selected Frames remains in `3 Review` and still supports Select All Visible Frames.
- Soft-delete/hide remains traceable and hidden rows remain excluded from preprocessing, training, and validation.
- PiSD V7 labels/records/overlay support is unchanged.
- Preprocess auto workflow and training GPU device controls are unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.13` install.
- Existing PiSD sessions do not need migration.
- Existing hidden-frame flags and edited labels remain compatible.
- Existing saved layouts may reset because `FORMAT_VERSION` changed.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_13` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_13.md`
  - `PATCH_NOTES_piTrainer_0_6_12.md`
  - `PATCH_NOTES_piTrainer_0_6_11.md`
  - `PATCH_NOTES_piTrainer_0_6_10.md`
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
  - V6.12 validation import fix, TensorFlow log handling, and queued edit responsiveness;
  - V6.13 simple model/view Record Preview table.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_13_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Record Preview panel, preview service, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.14`;
  - `PATCH_VERSION` reports `piTrainer_0_6_14`;
  - `FORMAT_VERSION` reports `0_6_14_sortable_record_preview`;
  - Record Preview uses `QTableView` / `QAbstractTableModel`;
  - Record Preview no longer uses `QTableWidget` / `QTableWidgetItem`;
  - table sorting is enabled;
  - default sorting targets `frame_id`;
  - sorted rows are mapped back to source dataframe rows;
  - selection restore hooks are connected around model sort/layout changes.
- Compared the working tree against fresh V6+0.6.1 through 0.6.13 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Direct PySide6 smoke testing was not performed in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow validation/training was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- Header sorting is compile/AST/static verified but should still be confirmed in the live Windows GUI.
- Sorting by edited steering/speed values updates the displayed cell immediately, but it does not automatically move the row while the edit debounce is saving. Click the header again if a manually sorted numeric column needs to be refreshed after edits.
