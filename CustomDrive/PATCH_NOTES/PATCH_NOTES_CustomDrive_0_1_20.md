# CustomDrive 0_1_20 Patch Notes

## Request summary
Add an **AI Settings** button to the current PiServer-style CustomDrive GUI so the user can:
- upload an object-detection model from PC
- select a model
- delete a model
- deploy a model
- overlay object-detection output on the live preview frame

## Root cause / gap
The current GUI had no object-detection model-management path. The earlier idea of reusing PiServer's steering/throttle `ModelService` was the wrong model type for CustomDrive. CustomDrive needs **object detection**, not driving regression output.

## Files changed
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/config/manual_control.json`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_20.md`

## Exact behavior changed
1. Added a new top-right **AI Settings** button beside the existing settings buttons.
2. Added a new AI modal window using the same overlay-window style as the rest of the GUI.
3. Added upload support for:
   - `.tflite`
   - optional matching `.txt` labels file
   - optional matching `.json` config file
4. Added model listing, selection, delete, and deploy routes.
5. Added a new `ObjectDetectionService` dedicated to TFLite object detection for CustomDrive.
6. Added live preview overlay support:
   - when a detector is deployed and overlay is enabled, the server draws detection boxes and labels on the live preview stream
   - when no detector is deployed, the preview stays unchanged
7. Added AI config persistence in `config/manual_control.json`:
   - deployed model name
   - overlay enabled
   - confidence threshold
   - IoU threshold
   - overlay FPS cap
8. Added an AI status metric in the merged status/system panel.

## Notes on model packaging
This patch expects a detector bundle by **same filename stem**, for example:
- `my_detector.tflite`
- `my_detector.txt`
- `my_detector.json`

Only the `.tflite` file is required. The `.txt` and `.json` sidecars are optional.

## Verification performed
- `python -m compileall CustomDrive`
- imported the new object-detection service successfully
- verified manual-control config normalization includes the new `ai` block
- verified patch was prepared as a patch-only zip with top-level `CustomDrive/` paths

## Known limits / next steps
- This patch supports **TFLite object detection** only; it does not add Ultralytics `.pt` runtime directly.
- Detector output shape handling is written to support common TFLite detector/YOLO export layouts, but some custom-export formats may still need adaptation.
- Overlay inference runs on the Pi inside the web preview path, so model size and FPS should be tuned for Raspberry Pi performance.
- This patch does **not** use detector output to drive the car automatically; it only manages models and overlays detections on the live frame.
