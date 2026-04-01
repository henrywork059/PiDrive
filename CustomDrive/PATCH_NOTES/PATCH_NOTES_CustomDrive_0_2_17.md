# CustomDrive 0_2_17 Patch Notes

## Request summary
Patch the current CustomDrive detector/overlay path so the deployed TFLite model from CustomTrainer is more likely to produce usable detections in the GUI overlay, and add clearer debug visibility for the actual parsed output layout.

## Root cause
The latest debug output showed that the detector was reaching the TFLite runtime successfully (`ready: true`, valid input/output shapes, deployed model name present), but the selected parser variant still decoded zero usable detections. The debug snapshot showed a 6-column output (`[1,300,6]`) with zero scores under the current `xyxy_score_class` interpretation, which strongly suggested a layout mismatch rather than a simple overlay-drawing failure.

There was also a secondary interpreter safety issue: some TensorFlow Lite interpreter builds are sensitive to retained tensor references, so output handling needed to copy the tensor data defensively before downstream parsing.

## Files changed
- `CustomDrive/custom_drive/tflite_perception.py`
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`

## Exact behavior changed
1. **More flexible 6-column TFLite output parsing**
   - Added support for multiple 6-column detection layouts instead of assuming only `xyxy_score_class`.
   - The parser now tries these layouts and selects the best one based on decoded detections and score statistics:
     - `xyxy_score_class`
     - `xyxy_class_score`
     - `yxyx_score_class`
     - `yxyx_class_score`
   - This is intended to better match exported detector variants that package score/class columns differently.

2. **Safer XYXY conversion for direct box outputs**
   - Added direct box conversion for `xyxy` and `yxyx` style rows.
   - Normalized coordinates are scaled back up to model input size before later frame-space rescaling.

3. **Interpreter output copied defensively**
   - The inference path now copies the output tensor into a standalone NumPy array before parsing.
   - This reduces the chance of interpreter internal-reference issues on some TFLite runtimes.

4. **Automatic synthetic label expansion improved**
   - If no `labels.txt` is present, synthetic labels are now updated using the class count actually inferred from parsed detections/debug info instead of relying only on static output-shape guesses.

5. **AI debug output improved**
   - Added these fields to GUI AI debug:
     - `score_col`
     - `class_col`
     - `coord_order`
   - Added the selected score/class column pairing into the overlay debug text on the frame itself.

6. **Asset version bumped**
   - GUI asset version updated to `0_2_17` so the browser is more likely to load the patched JS immediately after refresh.

## Verification actually performed
- Inspected the current reconstructed CustomDrive code state built forward from:
  - `CustomDrive_0_2_0.zip`
  - `CustomDrive_0_2_15_patch.zip`
  - `CustomDrive_0_2_16_patch.zip`
- Reviewed the current `CustomTrainer` Pi runtime parser in:
  - `CustomTrainer/custom_trainer/assets/pi_runtime/run_tflite_detect.py`
- Ran:
  - `python -m py_compile` on the patched Python files
  - `python -m compileall CustomDrive`
- Verified the patch package contains only changed/new files plus this patch note.

## Known limits / next steps
- This patch improves parser compatibility and debug visibility, but it cannot guarantee that the specific model will produce boxes without checking the next debug output on the Pi.
- If detections are still zero after this patch, the next likely step is to inspect one or more raw rows from the model output and add a model-specific parser variant based on the actual score/class field distribution.
- If you want real class names on overlay, `labels.txt` should still be uploaded alongside the model whenever available.
