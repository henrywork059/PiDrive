# CustomDrive 0_3_3 Patch Notes

## Request summary
Patch the current CustomDrive AI overlay/backend again so that:
- the debug / AI panel stops accidentally colliding with live overlay inference,
- the active backend path uses the current inference flow instead of triggering extra interpreter calls just from opening the debug UI,
- the 6-column TFLite parser can search more possible packed layouts instead of only assuming the score/class columns are the last two columns,
- and the debug output becomes more useful for tracking the real packed-column choice.

The user also asked whether uploading only the `.tflite` file could be the cause. This patch keeps labels/config sidecars optional, but does **not** assume missing sidecar files are the root cause of the live interpreter/reference error.

## Root cause
There were two main backend issues plus one parser limitation.

### 1) The AI debug route could still run inference concurrently with the overlay path
Even after the previous interpreter-metadata cleanup, the GUI still had a second path that could force a live inference:
- opening / refreshing the AI panel,
- clicking AI debug,
- and the overlay preview loop.

That meant the same interpreter could still be asked to infer from overlapping call paths. The user's timing log strongly matched that pattern:
- one normal ~1.1s inference,
- followed almost immediately by a very fast failure.

So even if the TFLite runtime metadata handling was improved, the app still needed stronger single-owner inference behavior.

### 2) The frontend was still auto-calling the debug inference route too aggressively
The AI settings UI was still calling the debug endpoint during normal modal-opening and refresh flows. That meant the backend could be asked to infer just because the user opened the AI modal, even when the overlay was already active.

That is not the behavior the user wanted.

### 3) The 6-column parser search space was still too narrow
The previous parser only tried a small set of 6-column layouts:
- `xyxy_score_class`
- `xyxy_class_score`
- `yxyx_score_class`
- `yxyx_class_score`

That is fine for the most common packed NMS output, but it is still too narrow if the model bundle/export uses a different packed-column order.

The user's latest debug snapshot showed:
- clear class-like values in one column,
- zero score behavior in the currently selected score column,
- and no decoded detections.

That means the live parser needed a broader packed-column search rather than only repeating the same last-two-column assumption.

## Files changed
- `CustomDrive/custom_drive/tflite_perception.py`
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_3.md`

## Exact behavior changed

### 1) Interpreter access is now serialized inside `TFLitePerception`
A dedicated invoke lock now guards the actual:
- `set_tensor()`
- `invoke()`
- `get_tensor()`

sequence.

That means even if another caller reaches the perception layer unexpectedly, the interpreter itself still has a single active inference owner.

### 2) AI debug inference is no longer auto-run just from opening the AI modal
The frontend AI settings flow was updated so that:
- opening the AI modal no longer forces a live inference,
- refreshing the model list no longer forces a live inference,
- deploy flow no longer immediately forces an extra debug inference after deployment.

The explicit **Run AI Debug** button still exists, but now it is the only normal UI action that requests a fresh debug inference.

### 3) `/api/ai/debug` now separates “show latest debug state” from “run a new inference”
The backend route now supports the idea of:
- returning the latest debug state/history without forcing inference,
- only running a new inference when explicitly requested.

This keeps the current debug/log information copyable without repeatedly touching the live interpreter.

### 4) Debug inference now shares the same inference lock behavior as overlay inference
If a debug inference is explicitly requested while the detector is already busy, the service now skips the extra inference attempt and records a backend log entry instead of piling another call into the same interpreter.

### 5) The 6-column TFLite packed-layout parser is now broader
For `[N,6]` outputs, the parser now searches a wider set of packed-column interpretations by trying different:
- score columns,
- class columns,
- coordinate column groups,
- coordinate modes (`xyxy`, `yxyx`, `xywh`).

This is more robust when the export/runtime bundle does not place score/class in the previously assumed last-two-column layout.

### 6) 6-column ranking now penalizes all-zero score columns more strongly
The 6-column ranker now considers extra score-column behavior, including:
- non-zero ratio,
- positive ratio,
- stronger preference for real non-zero confidence-like columns,
- stronger penalty for all-zero “score” columns.

That means a candidate with a dead score column is less likely to win just because its paired class column looks structurally plausible.

### 7) Debug output now shows more packed-layout information
The AI debug text now includes / can surface:
- `coord_cols`
- per-variant non-zero score ratio
- candidate coordinate ordering information

This makes it easier to see whether the parser is still choosing the wrong packed-column interpretation.

### 8) Safer 2D output normalization for `[N,6]`
The normalization logic was tightened so a genuine 6-column packed detection output is less likely to be incorrectly transposed in small synthetic / low-count cases.

### 9) GUI asset version bumped forward
The GUI control app version string was updated to `0_3_3` so the browser is more likely to fetch the new frontend JS immediately after refresh.

## Verification actually performed
- Re-read the relevant recent CustomDrive patch notes before patching, especially:
  - `0_2_17`
  - `0_3_1`
  - `0_3_2`
- Inspected the real current reconstructed CustomDrive code state built forward from:
  - `CustomDrive_0_3_0.zip`
  - `CustomDrive_0_3_1_patch.zip`
  - `CustomDrive_0_3_2_patch.zip`
- Ran Python syntax checks on:
  - `tflite_perception.py`
  - `object_detection_service.py`
  - `gui_control_app.py`
- Ran:
  - `python -m compileall CustomDrive/custom_drive`
- Ran JavaScript syntax check on:
  - `CustomDrive/custom_drive/gui_web/static/app.js`
- Ran parser smoke tests for:
  - standard packed `xyxy + score + class` output
  - non-standard shifted packed 6-column output
- Verified the new parser can resolve both tested layouts and report the selected coordinate columns.

## Known limits / next steps
- I still did **not** claim live Pi camera / live hardware validation in this container.
- Missing `labels.txt` or `model_config.json` can still reduce label names / default settings quality, but that does **not** look like the main cause of the interpreter-reference failure shown in the user's logs.
- If the next live debug snapshot still shows all score-like columns effectively dead, the next step is likely to inspect a small sample of raw output rows from the live model and lock in the exact export-specific packed layout instead of only using heuristics.
- This patch intentionally keeps the recent 2x arm-speed change and the copyable debug history behavior; it does not roll those back.
