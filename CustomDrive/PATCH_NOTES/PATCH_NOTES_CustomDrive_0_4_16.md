# PATCH NOTES — CustomDrive_0_4_16

## Request summary
Patch the Mission 1 object-box problem after code review showed that the detected-object boxes were still not drawing correctly from the detector coordinates.

The immediate user request for this patch was:
- inspect the code to find the problem
- patch it

This patch keeps the accepted Mission 1 web session flow from the latest `0_4_x` line, including:
- organised Mission 1 dashboard layout
- route -> camera -> model -> per-frame inference pipeline
- Pi-side annotated frame upload
- web detection table and overlay viewer
- selected-model / upload-model workflow
- target list, coordinates, confidence, and FPS display

No Mission 1 route sequencing, motor behavior, or web-panel click behavior was intentionally changed in this patch.

## Cause / root cause
The actual box bug was in the Mission 1 detector parser, not mainly in the viewer overlay code.

### Main root cause
In `CustomDrive/custom_drive/mission1_tflite_detector.py`, the 6-column detection-output branch handled rows in this form:
- `box0, box1, box2, box3, score, class_id`

But that branch returned the first four values directly as boxes without decoding normalized coordinates first.

So when a TFLite model returned normalized 6-column boxes such as values in the `0.0 .. 1.0` range, the Mission 1 detector passed those tiny values forward as if they were already input-image pixel coordinates.

That caused the downstream box coordinates to be far too small for both:
- Pi-side annotation in `mission1_session_app.py`
- browser-side overlay drawing in `mission1_web/static/app.js`

The result was that detections could still appear in the object list, but the boxes drawn around the image were missing or effectively collapsed.

### Secondary root cause caught during verification
While testing the detector fix, a second parser issue was found:
- when a 6-column output contained exactly one detection row, `np.squeeze()` could collapse the array from shape `(1, 6)` into shape `(6,)`
- after that collapse, the 6-column parser branch was skipped entirely
- this could make a single detected object disappear from the box path even though the detection payload itself should have been usable

That second problem was fixed in the same forward patch because it affects the same Mission 1 box-rendering pipeline.

## Files changed
- `CustomDrive/custom_drive/mission1_tflite_detector.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_16.md`

## Exact behavior changed

### 1. 6-column detector boxes are now decoded before scaling back to the frame
The Mission 1 detector now decodes 6-column outputs through a dedicated helper before `_scale_boxes()` is applied.

That helper now supports the common 6-column cases needed by the current Mission 1 line:
- normalized `xyxy + score + class_id`
- pixel-space `xyxy + score + class_id`
- normalized `xywh + score + class_id`
- pixel-space `xywh + score + class_id`

The parser now:
- detects whether the 6-column box coordinates look normalized
- scales normalized values up to the model input size first
- detects whether the 4 box values look like `xywh` rather than `xyxy`
- converts `xywh` to `xyxy` when needed
- only then returns boxes for the normal Mission 1 frame-scaling step

This keeps the downstream box path aligned with the existing Mission 1 annotation and overlay logic.

### 2. Single-row 6-column outputs are now preserved
The Mission 1 parser now explicitly reshapes a squeezed `(6,)` output back to `(1, 6)` when needed.

This prevents a single detection from being silently skipped by the 6-column parser path.

### 3. The patch is isolated to the detector path only
This patch deliberately does **not** change:
- Mission 1 route parsing
- route execution order
- camera startup order
- model startup order
- Mission 1 web layout
- Mission 1 JavaScript click bindings
- target-follow motor rule
- object-table payload structure used by the web UI

The goal of `0_4_16` is to fix the real box-coordinate bug without rolling back any accepted Mission 1 session behavior from `0_4_13` to `0_4_15`.

## Verification actually performed
The following checks were actually performed:

1. Reviewed the recent Mission 1 patch notes to avoid rollback risk:
   - `0_4_12`
   - `0_4_13`
   - `0_4_14`
   - `0_4_15`
2. Inspected the actual current Mission 1 code paths in:
   - `mission1_session_app.py`
   - `mission1_web/static/app.js`
   - `mission1_tflite_detector.py`
3. Confirmed the main box-drawing bug was in the detector parser rather than the overlay rendering code.
4. Updated the Mission 1 detector so 6-column normalized boxes are decoded into model-input pixels before the existing `_scale_boxes()` frame-mapping step.
5. Added a second parser fix so a single 6-column detection row is reshaped correctly after `np.squeeze()`.
6. Ran Python compile validation successfully on the patched detector file.
7. Ran code-level detector sanity checks for these 6-column cases:
   - normalized `xyxy`
   - normalized `xywh`
   - pixel-space `xyxy`
8. Confirmed the patch zip is patch-only, keeps the top-level `CustomDrive/` folder, and does **not** include `__pycache__` or `.pyc` files.

## Known limits / next steps
1. This patch fixes the Mission 1 box path at code level, but it was not tested here against the user's exact deployed TFLite model on real Pi hardware.
2. If boxes still appear in the wrong place after this patch, the next likely issue would be one of these model-specific output-layout differences:
   - `ymin, xmin, ymax, xmax` ordering instead of `x1, y1, x2, y2`
   - a model-specific custom output tensor structure
3. If that happens, the next debugging step should log one raw detection row from the active model output and compare it directly against the frame and object table.
4. This patch does not change the earlier `0_4_15` zip packaging mistake. It only ensures that **this** forward patch zip is packaged correctly without cache files.
