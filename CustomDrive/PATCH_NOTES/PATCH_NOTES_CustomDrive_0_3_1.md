# CustomDrive 0_3_1 Patch Notes

## Request summary
Patch the current `CustomDrive_0_3_0` baseline so that:
- the TFLite GUI overlay stops mis-parsing multi-class 6-column detector output,
- the AI debug window becomes usable for copying and tracking instead of constantly being overwritten,
- and the arm movement speed is doubled.

The user also clarified that the current focus is the GUI detector/overlay path rather than the mission label flow.

## Root cause
There were two main problems and one requested behavior update.

### 1) Wrong 6-column parser variant could still win
The latest debug output showed:
- `raw_shape: [1,300,6]`
- `variant: xyxy_class_score`
- `score_max: 4.0000`
- `labels_mode: synthetic`
- `class_count: 1`

That combination strongly indicated that the parser selection heuristic was still vulnerable to choosing a variant where the supposed score column actually looked like class IDs. In other words, the parser was previously ranking variants too heavily by decoded count / raw score magnitude, and not strongly enough by whether the chosen score column really behaved like a confidence column.

That causes two visible failures:
- inflated or nonsense detection counts,
- synthetic labels collapsing to the wrong class count even when the model actually has several classes.

### 2) AI debug text was being overwritten continuously
The GUI already had an AI debug box, but it was refreshed repeatedly by normal status polling. That made it difficult to:
- copy the current snapshot,
- keep a specific failure visible,
- or compare multiple debug states over time.

### 3) Arm speed needed to be increased without forcing a config reset
The request was to double the arm speed. The current speed behavior was controlled by runtime config values, so simply replacing the config file would risk rolling back user-local settings. The speed change therefore needed to be applied in code and remain backward-compatible with existing configs.

## Files changed
- `CustomDrive/custom_drive/tflite_perception.py`
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_1.md`

## Exact behavior changed

### 1) 6-column TFLite parser selection is now more class/score aware
For `[N,6]` detector outputs, each candidate interpretation now records column profiles before the final variant is chosen.

The parser now evaluates whether a candidate score column behaves like a real confidence column by checking things such as:
- how many values fall inside a normal confidence range,
- whether the column looks overly integer-like,
- whether the paired class column looks integer-like and class-like,
- and whether the candidate is therefore a more plausible `score/class` interpretation.

This reduces the chance that a class-ID column such as `0..4` will be mistaken for confidence.

### 2) AI debug now shows candidate variant summaries
The AI debug snapshot now includes a compact summary of all tested 6-column variants, including:
- variant name,
- decoded count,
- score max,
- selected score/class columns,
- score-in-range ratio,
- integer-likeness of the class column,
- approximate class uniqueness.

This makes it much easier to see why a given variant was selected.

### 3) AI debug snapshot can now be frozen and copied
The AI settings modal now adds:
- **Freeze Snapshot / Resume Snapshot**
- **Copy Snapshot**
- **AI debug history**
- **Copy History**
- **Clear History**

The current debug snapshot can now be frozen so normal polling does not overwrite it while the user is reading or copying it.

### 4) AI debug history is now tracked in the browser session
Instead of only showing the latest debug text, the GUI now keeps a rolling local history of distinct AI debug snapshots.

That means the user can now:
- compare multiple states across deploy/debug attempts,
- keep older errors visible,
- copy the whole recent debug history in one go.

### 5) Arm movement speed is doubled without requiring a config wipe
A new arm config key is now supported:
- `speed_multiplier`

It defaults to `2.0` when missing, so existing configs automatically get the requested 2x speed behavior without needing a manual config replacement.

The multiplier is applied to:
- lift motion timing (faster lift updates)
- gripper motion rate (faster open/close movement)

The arm status payload now also exposes the effective `speed_multiplier`.

### 6) GUI asset version bumped forward
The GUI control app version string was updated to `0_3_1` so the browser is more likely to fetch the patched frontend assets instead of keeping the previous cached JS/CSS.

## Verification actually performed
- Read the recent CustomDrive patch notes relevant to this area, especially:
  - `0_2_15`
  - `0_2_16`
  - `0_2_17`
- Inspected the real uploaded `CustomDrive_0_3_0.zip` code before patching.
- Ran Python syntax checks on:
  - `tflite_perception.py`
  - `arm_service.py`
  - `manual_control_config.py`
  - `gui_control_app.py`
- Ran:
  - `python -m compileall CustomDrive`
- Ran a parser smoke test for a synthetic `[N,6]` tensor in `xyxy + class + score` order and verified:
  - selected variant became `xyxy_class_score`
  - inferred class count expanded to 5
  - the selected score/class columns matched the intended layout
- Ran JavaScript syntax check on:
  - `CustomDrive/custom_drive/gui_web/static/app.js`

## Known limits / next steps
- I did **not** claim live Pi camera / live hardware TFLite runtime testing in this environment.
- This patch makes the parser much harder to fool with class-ID columns, but if your exported model uses a different 6-column semantic layout again, the next step would be to inspect one or two raw rows from the live tensor and add that exact layout explicitly.
- The AI debug history is currently browser-session history, not a persistent server-side log file. It solves the immediate copy/track problem in the GUI without adding another persistence layer.
