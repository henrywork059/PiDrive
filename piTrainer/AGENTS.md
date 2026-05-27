# piTrainer AI Agent Instructions

Use this file when an AI coding assistant continues piTrainer work inside the PiDrive monorepo.

## Component scope

- Work only inside `piTrainer/` unless the user explicitly asks to change another PiDrive component.
- Treat `piTrainer/main.py` as the real entry point. Do not invent or document a different launcher.
- Preserve the exact `piTrainer/` folder structure when preparing patches.

## Current baseline and version line

- Latest accepted full baseline: `piTrainer_0_7_0` / V7.
- Future patch-only zips should build forward as `piTrainer_0_7_1_patch.zip`, `piTrainer_0_7_2_patch.zip`, and so on.
- Patch zips must include only changed/new files plus patch notes.
- Patch notes belong in `piTrainer/PATCH_NOTES/`.

## Anti-rollback requirements

Before editing, inspect:

1. The current files in `piTrainer/`.
2. The latest piTrainer patch note.
3. The previous three piTrainer patch notes when available.

Do not restore older copies of files by accident. Do not remove accepted V7 behaviour unless the user explicitly asks.

Preserve these accepted V7 behaviours:

- PiSD V7 `labels.jsonl` and `records.jsonl` support.
- PiSD V7 saved overlay metadata and overlay redraw support.
- Manual-drive preprocessing support.
- Training-start preflight fixes.
- Record Preview uses a simple read-only `QTableView`/`QAbstractTableModel` list with `frame_id` as the first column, header sorting enabled, default sort by `frame_id`, optimised single-frame edit, multi-select soft-delete/hide, bulk selected-frame edit, and merge support.
- Full-width splitter layout.
- Horizontal scrollbars only when panel content is reduced too far.
- Compact top guide banner.
- Green action buttons without the old `Next Step:` label prefix.
- Yellow amber buttons only for prerequisite/setup actions that should normally be completed before the main green action.
- Central style/format control through `piTrainer/piTrainer/ui/formatting.py` and `piTrainer/piTrainer/ui/styles.py`.
- Central colour tokens through `piTrainer/piTrainer/ui/theme.py`; do not scatter local hex colours through panels/services.
- Visible version in the app window/status area.

## UI and layout rules

- Keep the app visually uniform across tabs and panels.
- Use central formatting/style files before adding one-off widget styling.
- Keep main action sections expanded by default.
- Collapse only detailed settings and fine-detail data tools by default.
- Keep panel content reachable with scrollbars when a splitter panel is reduced.
- Put buttons near the thing they affect; avoid generic catch-all action panels.
- Keep playback controls directly under the image preview.
- Keep Data Review tabs ordered as `1 Records`, `2 Stats`, `3 Plot` unless the user asks otherwise.
- Keep Data Workflow tabs ordered as `1 Load`, `2 Manage`, `3 Review` unless the user asks otherwise.
- Keep Frame Filter in `2 Manage` beside Data Control.
- Keep Bulk Edit Selected Frames in `3 Review`; it edits only steering or only speed one at a time, has a Select All Visible Frames setup button, requires an overwrite checkbox plus a warning confirmation dialog, and must use the batch JSONL updater so each selected session metadata file is scanned once rather than once per selected frame.
- Keep Merge Sessions in `3 Review`, collapsed by default.
- Keep `frame_id` as the first visible Record Preview table column.
- Keep Record Preview deliberately simple: use the read-only model/view table, keep header sorting inside the model with explicit source-row mapping, keep the default sort on `frame_id`, keep the visible columns short and stable, and do not reintroduce `QTableWidget` item-based current-cell logic.
- Keep the Record Preview table horizontally anchored to the first column after multi-row selection; do not let Qt selection/current-cell behaviour scroll it to the second column, and do not force the selected row into the vertical centre on normal click/selection. Use ensure-visible scrolling only when keyboard/playback navigation needs it.
- Keep Up/Down navigation cycling through Record Preview rows when the table has focus. Down moves to the next frame and wraps from the last row to the first; Up moves to the previous frame and wraps from the first row to the last.
- Keep batch frame deletion as a soft-delete/hide action tied to the Data Control confirmation checkbox; do not physically remove JSONL rows or image files, and do not restore repeated confirmation popups for every delete.
- Keep compact banner guide labels free from the old `Show:` prefix.
- Keep Browse/location-picking and other prerequisite setup buttons yellow-forward amber, not brown.
- Keep green for main actions, including `nextStep` and `primary` action roles.
- Keep scrollbars readable but still slim; V7 preserves the V6.6 scrollbar sizing: about 30% thicker than V6.5 after user review.
- Keep splitter handles slim so they do not dominate narrow panels.
- Keep the Edit Steering slider and bulk steering slider fill centred on neutral steering instead of filling from the left edge.
- Hidden/deleted frames must remain traceable in `labels.jsonl` / `records.jsonl` using hidden flags, and must be excluded from active dataframes, preprocessing, training, and validation. Validation pages must import and use the shared `without_hidden_rows()` guard.
- Single-frame edits from Image Preview should not rebuild the whole Record Preview table unless the edited value makes the row fail the active filter. Use targeted visible-row updates, delayed plot refresh, queued/debounced JSONL writes that do not block clicking into the next frame, and cached JSONL parsing to keep clicking/dragging responsive. Background edit commits must preserve the user's current Record Preview selection.
- Keep the Preprocess page arranged around the `1 Auto` fast path and `2 Settings` custom path. Most users should be able to click the green `Auto Preprocess Active Data` button after loading sessions. The recommended/default/auto preprocess recipe must include one horizontal flip copy for every active frame. Every horizontal-flip copy must invert steering, preserve speed/throttle, keep a traceable `source_steering`, and remain label-safe in preprocessing, training, validation, and preview paths. Optional filters/augmentation/save-maintenance controls should stay behind collapsed advanced sections.
- Keep Train Config `Training device` support. Default to `Auto (GPU if available)`, allow `CPU only` and `GPU only`, and configure/log TensorFlow GPU availability inside the training worker without importing TensorFlow on the UI thread. Keep TensorFlow startup noise reduced by setting `TF_CPP_MIN_LOG_LEVEL` before any TensorFlow import, but do not silently disable oneDNN optimisations.
- Keep Train Config defaults beginner-friendly: split mode defaults to `Random rows`, `session_split` defaults to false, and default epochs is `100`. Do not restore the older `By session` / 10-epoch defaults unless the user asks.
- Keep preprocessed synthetic/augmentation rows traceable: every generated row must have its own `frame_id` beginning with `s_`, plus `source_frame_id`, `is_synthetic=True`, and `synthetic_variant` metadata. Do not let horizontal flip, colour, or turn-boost copies reuse the original source `frame_id`.
- Keep the Train page as a three-column workspace: left `Training Workflow`, middle `Training History / Log`, and right `Epoch Frame Review`. Do not move frame review back above the history/log stack unless the user asks.
- Keep the Validation page as a three-column workspace: left `Validation Workflow`, middle `Validation Plot / Log`, and right `Validation Frame Review`. Do not return frame review to a vertical stack above/below plot/log unless the user asks.

- Keep Export page output user-readable. TensorFlow/Keras/TFLite may print temporary SavedModel endpoint details, C++ converter warnings, and quantization diagnostics even when export succeeds; export code should capture/summarise this chatter, log created artifact paths and sizes, and clearly state that the size-optimised TFLite file keeps float32 input/output for PiDrive runtime compatibility.

## Packaging checklist

For each patch:

1. Patch only the required files.
2. Update `piTrainer/piTrainer/version.py`.
3. Update `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md` when UI/style/colour rules change.
4. Add detailed patch notes in `piTrainer/PATCH_NOTES/`.
5. Run `python -m compileall` or AST parsing when possible.
6. Remove `__pycache__` folders before packaging.
7. Zip with `piTrainer/` as the top-level folder and no extra nesting.

## Verification wording

Only claim checks that were actually run. Be clear about anything not tested, especially live PySide6 rendering, real PiSD import, or TensorFlow training.
