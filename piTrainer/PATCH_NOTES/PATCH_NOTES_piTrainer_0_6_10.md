# PATCH NOTES — piTrainer_0_6_10 Record Preview Anchoring, Navigation, and Edit Optimisation Patch

## Request summary
- Record Preview still sometimes jumps horizontally to the second column when multiple frames are selected.
- Improve and optimise the edit-frame-data function because it is too slow, especially when clicking or dragging on the frame/image to edit steering and speed.
- Up and Down arrow keys should cycle through frames.
- Add a Select All function to Bulk Edit.

## Cause / root cause
The earlier first-column anchoring fix reset the horizontal scrollbar after selection changes, but Qt can still auto-scroll again after current-cell changes, sorting, selection expansion, or resize events. If the current cell remained in column 2 or another later column, Qt could bring that cell into view and shift the table away from the first column.

The single-frame image edit path also rebuilt the full Record Preview table after each saved steering/speed edit. That was unnecessarily expensive because one row changed, but the whole preview table, plot, and selection state were refreshed. Repeated click/drag edits could also trigger frequent JSONL re-reads and rewrites.

Bulk Edit already supported multi-row editing, but selecting all visible preview rows still required manual table selection.

## Files changed
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Adds `CyclingPreviewTable` so Up/Down cycles through visible frame rows when the Record Preview table has focus.
  - Normalises current-cell selection back to column 1 / `frame_id` without clearing multi-row selections.
  - Re-anchors the horizontal scrollbar after selection changes, sorting/current-cell changes, Select All, and keyboard movement.
  - Adds `select_all_records()` for bulk-edit use.
  - Adds `update_record_values()` so single-frame edits can update the visible steering/speed cells without rebuilding the whole table.
- `piTrainer/piTrainer/panels/data/bulk_edit_panel.py`
  - Adds `Select All Visible Frames` setup button inside Bulk Edit Selected Frames.
  - Wires the button through a callback supplied by the Data page.
- `piTrainer/piTrainer/pages/data_page.py`
  - Wires Bulk Edit Select All to Record Preview.
  - Changes single-frame image edits to update loaded dataframes and the visible preview row directly when the active filter still allows the row.
  - Rebuilds the preview only when an active speed/steering filter may exclude the edited row.
  - Adds a short delayed plot refresh after single-frame edits so the plot updates without blocking every small edit interaction.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Increases the edit commit debounce from 250 ms to 750 ms to avoid repeated JSONL writes during click/drag adjustments.
- `piTrainer/piTrainer/services/data/edit_service.py`
  - Adds a small JSONL parse cache keyed by file signature.
  - Reuses cached parsed metadata entries for repeated edits in the same session, reducing repeated re-read/re-parse overhead.
  - Keeps the existing full-file rewrite safety for JSONL while avoiding unnecessary parsing work.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_10_preview_navigation_edit_optimisation`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.10` / `piTrainer_0_6_10`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents Record Preview anchoring, Up/Down cycling, targeted single-frame edit updates, and Bulk Edit Select All.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions to preserve the new preview navigation, anchoring, and edit-performance rules.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_10.md`
  - This patch note.

## Exact behaviour changed
- Record Preview now repeatedly anchors back to the first column after selection/current-cell changes so multi-select should not leave the view starting at the second column.
- Up Arrow and Down Arrow inside the Record Preview table now move to the previous/next frame and wrap around at the first/last visible row.
- Bulk Edit now has a `Select All Visible Frames` button that selects every currently displayed Record Preview row.
- Single-frame edits from Image Preview now update the visible row values directly instead of rebuilding the full Record Preview table every time.
- The plot is refreshed on a short timer after single-frame edits instead of blocking every click/drag adjustment.
- JSONL parsing is cached for repeated same-session edits, so multiple edits to nearby frames avoid re-reading and re-parsing the same `labels.jsonl` / `records.jsonl` files each time.
- Image click/drag edits are debounced for 750 ms before committing to JSONL, reducing repeated writes during active adjustment.

## Behaviour intentionally not changed
- Data Workflow remains ordered as `1 Load`, `2 Manage`, `3 Review`.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot`.
- `frame_id` remains the first Record Preview column.
- Bulk Edit remains in `3 Review` and still applies only one field at a time:
  - `Apply Steering Only` changes steering only;
  - `Apply Speed Only` changes speed/throttle only.
- Bulk Edit still requires the overwrite checkbox and final confirmation dialog before writing.
- Soft-delete / hidden-frame handling from V6.8 is unchanged.
- Hidden frames remain excluded from active dataframes, preprocessing, training, and validation.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading and overlay redraw support are unchanged.
- V6.6 amber/green action colour semantics, scrollbar thickness, and centred steering sliders are unchanged.
- Batch JSONL bulk editing from V6.9 is preserved.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.9` install.
- Existing PiSD sessions do not need migration.
- The JSONL cache is in-memory only and validates against file modification time and size before reuse.
- JSONL files are still rewritten safely rather than modified in-place because line lengths can change when numeric labels change.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_9` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_9.md`
  - `PATCH_NOTES_piTrainer_0_6_8.md`
  - `PATCH_NOTES_piTrainer_0_6_7.md`
  - `PATCH_NOTES_piTrainer_0_6_6.md`
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
  - V6.4 first-column anchoring intent and removal of `Next Step:` / `Show:` prefixes;
  - V6.5 central theme token system;
  - V6.6 amber/green action colour semantics and centred steering slider;
  - V6.7 Bulk Edit Selected Frames panel and one-field-at-a-time edit safety;
  - V6.8 traceable soft-delete / hidden-frame behaviour;
  - V6.9 fast batch JSONL bulk-edit path.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_9_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Data page, Record Preview panel, Bulk Edit panel, Image Preview edit flow, edit service, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a focused temporary-session edit-service test confirming:
  - repeated single-frame edits still update both `labels.jsonl` and `records.jsonl`;
  - the second edit sees and updates the cached data correctly;
  - batch steering-only edits still update selected rows and preserve speed/throttle.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.10`;
  - `PATCH_VERSION` reports `piTrainer_0_6_10`;
  - `FORMAT_VERSION` reports `0_6_10_preview_navigation_edit_optimisation`;
  - `CyclingPreviewTable` is present;
  - `select_all_preview_frames_for_bulk_edit` is wired;
  - `update_record_values()` is present;
  - JSONL caching is present;
  - Image Preview edit debounce is 750 ms.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4+0.6.5+0.6.6+0.6.7+0.6.8+0.6.9 to identify intended changed/new files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch targets Record Preview navigation and edit responsiveness.

## Known limits / next steps
- The table anchoring and keyboard cycling changes are compile/AST verified but still need live PySide6 GUI confirmation on Windows.
- Single-frame JSONL edits still rewrite the affected JSONL files after the debounce. This is safer than in-place modification, but very large sessions may still benefit from a future explicit Save Changes queue if the user wants edit batching across many manual clicks.
