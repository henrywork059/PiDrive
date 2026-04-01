# CustomDrive 0_2_16 Patch Notes

## Request summary
Fix the current CustomDrive AI overlay path so it is easier to tell whether:
- the TFLite model really loaded,
- detections are being decoded,
- boxes are being drawn,
- or the issue is elsewhere.

The user also asked to add a debug method to help inspect the problem.

## Root cause
There were two main problems in the current code path:

1. **Detection decoding was still too dependent on labels/config sidecars.**
   When a TFLite model was uploaded without a matching `labels.txt`, the decoder could still mis-read Ultralytics-style output layout because it relied too much on `num_classes` to decide whether to transpose and how many class channels to expect.

2. **The GUI gave almost no visibility into detector state.**
   The model could deploy successfully, preview frames could still render, and yet the user had no direct way to see whether the detector was producing:
   - zero candidates,
   - zero decoded boxes,
   - zero boxes after NMS,
   - missing labels,
   - or a parser/layout mismatch.

3. **AI settings were still too chatty.**
   The AI modal could post config updates repeatedly while open. That was not the root cause of missing boxes by itself, but it made the system harder to debug and likely contributed to longer-run instability.

## Files changed
- `CustomDrive/custom_drive/tflite_perception.py`
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_2_16.md`

## Exact behavior changed

### 1) TFLite output decoding is more robust
- Added stronger layout inference for common Ultralytics TFLite output shapes such as `[1, 6, N]`, `[1, 7, N]`, etc.
- The decoder no longer depends so heavily on `labels.txt` existing in order to transpose the output correctly.
- Added a fallback path that can synthesize temporary class names (`class_0`, `class_1`, ...) when labels are missing, so the detector can still produce visible boxes for debugging.
- The decoder now records which interpretation it used:
  - `xyxy_score_class`
  - `no_objectness`
  - `with_objectness`

### 2) Added detector debug status
- `TFLitePerception.status()` now exposes debug fields such as:
  - input shape
  - output shapes
  - labels mode (`file`, `synthetic`, `missing`)
  - chosen decode variant
  - layout (`as_is` / `transposed`)
  - candidate count
  - decoded count
  - NMS-kept count
  - class count
  - score max / mean
- `ObjectDetectionService` now keeps that debug data alongside the latest detections.
- Added a new route:
  - `/api/ai/debug`
- That route forces a single debug inference on the latest frame when possible and returns a compact JSON summary of the detector state.

### 3) Overlay now shows more useful debug context
- The AI overlay header still shows the active model name.
- When TFLite overlay is active, it now also shows a short debug summary directly on the frame:
  - raw output shape
  - selected decode variant
  - candidate count
  - decoded count
  - boxes kept after NMS
- This makes it easier to tell whether the issue is “no detections” versus “drawing failed.”

### 4) AI settings window now has a debug tool
- Added a **Run AI Debug** button in the AI modal.
- Added an **AI debug** text box that shows the current detector state in a readable form.
- Added an explicit **Save AI Settings** button.
- AI setting changes are still saved, but now through a short debounce instead of firing full-save requests as aggressively as before.

### 5) AI settings no longer drift the deployed model just by selection
- The GUI now tracks the actually deployed model separately from the currently selected dropdown item.
- Selecting a different model in the dropdown no longer silently rewrites the deployed model state before the user presses **Deploy Model**.

## Verification actually performed
- Inspected the real uploaded `CustomDrive_0_2_0.zip` stable baseline.
- Read the recent `CustomDrive` patch notes for `0_2_12`, `0_2_13`, `0_2_14`, and `0_2_15` before editing to avoid rolling back the current overlay/runtime direction.
- Inspected the current `CustomTrainer` Pi runtime detector parser and compared it against the current `CustomDrive` TFLite path.
- Reconstructed the current CustomDrive code state forward from the stable baseline and recent accepted `0_2_x` patches before applying this fix.
- Ran:
  - `python -m compileall CustomDrive`
- Ran local parser smoke checks for:
  - a no-objectness style tensor layout
  - an objectness style tensor layout
- Checked that the GUI JavaScript still parses successfully after the AI debug additions.

## Known limits / next steps
- I did **not** claim live Pi camera or live hardware inference testing here.
- This patch improves decoder robustness and adds visibility, but if the uploaded model still produces zero boxes after this patch, the next step is to inspect the model's exact output tensor semantics from the debug data on the Pi.
- The current preview loop is still active over long runtimes. If the Pi still freezes after this patch, the next fix should move overlay inference fully into a dedicated cached worker instead of the request path.
