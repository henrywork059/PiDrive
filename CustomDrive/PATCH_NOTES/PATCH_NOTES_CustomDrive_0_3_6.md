# CustomDrive 0_3_6 Patch Notes

## Request summary
Fix the current CustomDrive AI overlay because:
- the overlay now works on a PC webcam but not on the Raspberry Pi,
- and the drawn boxes/results do not match the known-good CustomTrainer export validation behavior.

This patch was made forward on top of the current accepted CustomDrive state, keeping the recent arm fixes and recent AI debug/log fixes intact.

## Anti-rollback review performed
Before patching, I checked:
- the current reconstructed code state built from `CustomDrive_0_3_0` plus accepted `0_3_1` to `0_3_5`
- the latest patch note: `0_3_5`
- the previous three recent notes: `0_3_4`, `0_3_3`, `0_3_2`
- the earlier AI-overlay note: `0_3_1`

That review was used to avoid rolling back:
- the accepted GUI direction
- the copyable AI debug/history behavior
- the no-overlapping-inference fixes
- the every-5-frame overlay cadence direction
- the 2x arm speed and later arm stability fixes

## Root cause
There were two linked problems.

### 1) Pi GUI overlay was not using the same kind of source frames as the PC webcam path
In the GUI app, the Pi camera service was started with preview enabled, but **processing frames were not explicitly enabled** when TFLite AI was active.

That matters because the Pi camera backend only keeps raw BGR processing frames when `processing_enabled` is true. Without that, the GUI overlay path often fell back to re-decoding the preview JPEG instead of using a fresh raw frame.

On PC/OpenCV capture, frames are still available even without that flag, so the webcam path could work while the Pi path lagged behind or behaved differently.

So the platform mismatch was largely caused by the GUI not turning on raw processing frames for the Pi path when AI was actually deployed.

### 2) The 6-column parser could still drift away from the exact CustomTrainer export runtime layout
The known-good CustomTrainer Pi runtime (`run_tflite_detect.py`) uses a simple 6-column expectation for exported detections:
- columns `0..3` = box coordinates
- column `4` = score
- column `5` = class id

The CustomDrive parser had added broader heuristic exploration to survive ambiguous models, but that also meant the live runtime could pick a different interpretation than the known-good export runtime.

That mismatch is especially risky when:
- the model is a standard CustomTrainer-exported detector,
- validation in the trainer/export runtime already works,
- but the live app still tries to reinterpret the same 6-column tensor more aggressively.

So even when overlay was running, the box/class interpretation could drift away from the export/runtime behavior that had already been confirmed working.

## Files changed
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/tflite_perception.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_6.md`

## Exact behavior changed

### 1) GUI now enables Pi raw processing frames whenever TFLite AI is deployed
A new internal sync step now keeps the camera service processing path enabled whenever:
- backend = `tflite`
- and a real model is deployed

This means the Pi GUI now keeps current raw frames available for:
- live overlay rendering
- explicit AI debug runs

That reduces the gap between:
- PC webcam behavior (which already had usable live frames), and
- Pi camera behavior (which previously could fall back to preview JPEG decoding only).

### 2) Overlay/debug now prefer raw Pi frames first
The GUI AI routes now try frame sources in this order:
1. `get_raw_frame(copy=True)`
2. `get_latest_frame(copy=True)`
3. JPEG decode fallback only if no raw frame is available

That keeps the Pi path closer to the same inference input quality/style used by the working PC path.

### 3) Standard CustomTrainer 6-column exported layout is now preferred when it is plausible
For `[N,6]` detector output, the parser now explicitly prefers the same fixed layout used by the CustomTrainer Pi runtime when that layout looks valid:
- `coord_cols = [0,1,2,3]`
- `score_col = 4`
- `class_col = 5`
- `coord_order = xyxy`

The broader heuristic search is still available as fallback for genuinely different 6-column layouts, but the standard export path now wins first when it is plausible.

This reduces the chance that CustomDrive will draw different boxes/classes than the already-validated export runtime for the same model.

### 4) GUI asset version bumped forward
The GUI version string was updated to `0_3_6` so the browser is more likely to fetch the latest GUI assets and route behavior after patching.

## Verification actually performed
- Reconstructed the active CustomDrive code state forward from:
  - `CustomDrive_0_3_0.zip`
  - `CustomDrive_0_3_1_patch.zip`
  - `CustomDrive_0_3_2_patch.zip`
  - `CustomDrive_0_3_3_patch.zip`
  - `CustomDrive_0_3_4_patch.zip`
  - `CustomDrive_0_3_5_patch.zip`
- Re-read the recent patch notes listed above before editing.
- Inspected the real GUI camera/overlay path in:
  - `custom_drive/gui_control_app.py`
  - `custom_drive/object_detection_service.py`
  - `custom_drive/tflite_perception.py`
- Compared the CustomDrive 6-column parsing path against the known-good CustomTrainer Pi runtime script:
  - `CustomTrainer/custom_trainer/assets/pi_runtime/run_tflite_detect.py`
- Ran Python syntax checks and:
  - `python -m compileall custom_drive`
- Ran a parser smoke test for standard exported `[N,6]` rows and verified the selected variant became:
  - `xyxy_score_class`
- Verified that the fixed-layout preference still leaves fallback parsing available for other layouts.

## Known limits / next steps
- I did **not** claim live Pi hardware testing in this container.
- This patch fixes the most likely platform-specific difference in the GUI path by enabling/using raw Pi frames for AI, but final live accuracy still depends on the real Pi camera image quality and settings.
- If detections still differ after this patch, the next thing to inspect is the actual Pi-side frame appearance going into the model versus the trainer/export runtime image appearance (for example brightness / white balance / colour balance / preview size).
- I intentionally kept the broader 6-column fallback logic in place so non-standard future models are not locked out, but standard CustomTrainer-exported models should now follow the same main layout as the known-good export runtime.
