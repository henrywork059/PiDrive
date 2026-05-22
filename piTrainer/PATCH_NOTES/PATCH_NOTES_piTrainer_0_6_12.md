# PATCH NOTES — piTrainer_0_6_12 Validation Import / Record Preview Scroll / Edit Responsiveness Patch

## Request summary
- The selected Record Preview frame should not always be forced into the middle row.
- Validation currently crashes with:
  - `NameError: name 'without_hidden_rows' is not defined`
- TensorFlow INFO messages appear in the PowerShell console when starting/running the app.
- Image Preview frame editing is still too slow, especially when clicking from one frame to another after editing.

## Cause / root cause
- `validation_page.py` used the hidden-row guard introduced for soft-delete safety but did not import `without_hidden_rows`.
- The Record Preview first-column anchoring logic called `scrollToItem(..., PositionAtCenter)` every time selection changed. That helped horizontal anchoring, but it also forced the selected row into the vertical centre of the table.
- Image Preview called `_flush_pending_commit()` when switching records. That meant clicking a different row after editing could synchronously write `labels.jsonl` / `records.jsonl` before the next frame appeared.
- Single-frame edits were still committed one record at a time. If several quick edits were pending, the same session metadata file could still be scanned and rewritten more than necessary.
- TensorFlow C++ INFO logging was not muted before later training/validation/export TensorFlow imports.

## Files changed
- `piTrainer/piTrainer/__init__.py`
  - Sets `TF_CPP_MIN_LOG_LEVEL=2` by default before normal piTrainer imports continue.
  - This reduces TensorFlow INFO noise without disabling oneDNN optimisations.
- `piTrainer/piTrainer/pages/validation_page.py`
  - Imports `without_hidden_rows` from the shared visibility service.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Stops using `PositionAtCenter` during normal selection anchoring.
  - Uses `EnsureVisible` only for programmatic navigation/focus actions.
  - Keeps repeated horizontal first-column anchoring so the table should not drift to column 2.
  - Allows targeted row updates to preserve the current selection when a delayed edit commit finishes after the user has already selected another frame.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Replaces synchronous edit flushing on row change with queued/debounced edit commits.
  - Reduces the edit debounce interval from 750 ms to 450 ms.
  - Emits multiple pending frame edits together when needed.
- `piTrainer/piTrainer/pages/data_page.py`
  - Handles queued Image Preview edits as a batch.
  - Preserves the user's current Record Preview selection when a delayed edit for a previous frame is committed.
  - Updates stats, table cells, and plot refresh once for a queued edit batch where possible.
- `piTrainer/piTrainer/services/data/edit_service.py`
  - Adds `update_frame_controls_many()` for queued Image Preview edits where each frame has its own steering/speed values.
  - Scans and rewrites each affected `labels.jsonl` / `records.jsonl` file once per queued edit batch, instead of once per pending frame.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_12_validation_scroll_edit_responsiveness`.
- `piTrainer/piTrainer/version.py`
  - Updates visible version metadata to `0.6.12` / `piTrainer_0_6_12`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the no-centre-row Record Preview rule, queued edit behaviour, and TensorFlow log handling.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve these fixes.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_12.md`
  - This patch note.

## Exact behaviour changed
- Validation no longer raises `NameError` when selecting validation, training, or filtered datasets.
- Record Preview still anchors horizontally to the first column, but normal mouse selection does not repeatedly centre the selected row vertically.
- Up/Down cycling and programmatic focus still ensure the selected row is visible.
- Clicking away from an edited frame no longer blocks on an immediate JSONL write before the next preview appears.
- Image Preview edits are queued and committed shortly after editing stops.
- If several frame edits are queued, piTrainer groups them by session and rewrites each affected metadata file once.
- A delayed commit for an older frame updates that row in place without stealing focus from the row the user is currently reviewing.
- TensorFlow INFO logs such as oneDNN/CPU-feature startup messages should be reduced during normal piTrainer launches.

## Behaviour intentionally not changed
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and saved overlay metadata support are unchanged.
- Soft-delete / hidden-frame flags remain traceable and hidden rows remain excluded from preprocessing, training, and validation.
- Data Workflow tab order remains `1 Load`, `2 Manage`, `3 Review`.
- Data Review tab order remains `1 Records`, `2 Stats`, `3 Plot`.
- `frame_id` remains the first Record Preview column.
- Up/Down still cycles through rows when the Record Preview table has focus.
- Bulk Edit Selected Frames remains one-field-at-a-time and still requires the overwrite checkbox plus final warning dialog.
- Bulk Edit `Select All Visible Frames` is unchanged.
- Physical image/JSONL deletion is still not restored; hide/delete remains soft-delete.
- Preprocess `1 Auto` / `2 Settings` workflow from 0.6.11 is unchanged.
- Training device choices from 0.6.11 remain unchanged.
- This patch does not set `TF_ENABLE_ONEDNN_OPTS=0`; users can still set that manually if they specifically want to disable oneDNN optimisations.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.11` install.
- Existing PiSD sessions and hidden flags do not need migration.
- Existing saved layouts may reset because `FORMAT_VERSION` changed for Record Preview behaviour and responsiveness rules.
- TensorFlow INFO suppression is done with `os.environ.setdefault`, so an advanced user can override `TF_CPP_MIN_LOG_LEVEL` before launching piTrainer.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_11` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_11.md`
  - `PATCH_NOTES_piTrainer_0_6_10.md`
  - `PATCH_NOTES_piTrainer_0_6_9.md`
  - `PATCH_NOTES_piTrainer_0_6_8.md`
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
  - V6.10 Record Preview anchoring, Up/Down cycling, Bulk Edit Select All, and targeted edit optimisation;
  - V6.11 Preprocess auto workflow and training device/GPU controls.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_11_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Data page, Record Preview panel, Image Preview panel, edit service, validation page, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a temporary-session queued multi-edit service test confirming:
  - two different frame edits with different steering/speed values update both `labels.jsonl` and `records.jsonl`;
  - unchanged rows stay unchanged;
  - matched frame counts are reported.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.12`;
  - `PATCH_VERSION` reports `piTrainer_0_6_12`;
  - `FORMAT_VERSION` reports `0_6_12_validation_scroll_edit_responsiveness`;
  - `validation_page.py` imports `without_hidden_rows`;
  - Record Preview no longer uses `PositionAtCenter`;
  - Image Preview no longer flushes pending edits synchronously inside `set_record()`;
  - `update_frame_controls_many()` is present.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4+0.6.5+0.6.6+0.6.7+0.6.8+0.6.9+0.6.10+0.6.11 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Direct PySide6 import/smoke testing was not possible because this sandbox does not have PySide6 installed.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow validation/training was not run.
- Actual GPU hardware execution was not tested in this sandbox.

## Known limits / next steps
- TensorFlow may still print some non-INFO warnings/errors when there is an actual driver or model issue; those should remain visible.
- Queued Image Preview edits are committed after a short debounce. If the app is forcibly killed immediately after an edit, a very recent queued edit may not have been written yet.
- A future patch could add a visible small "pending edit saved" indicator if live testing shows users need clearer save feedback.
