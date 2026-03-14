# PATCH NOTES - CustomTrainer (Pi-ready draft update)

## Goal
Update the object-detection trainer so the trained model is prepared to run on Raspberry Pi instead of stopping at generic desktop export.

## Main changes

### 1. Pi-oriented export defaults
- Changed the Export page default format to **TFLite**.
- Changed the default image size to **320** for lighter Pi inference.
- Added quantization choices:
  - `int8`
  - `float16`
  - `float32`
- Added optional embedded **NMS** export toggle.
- Added `dataset.yaml` input for **INT8 calibration**.

### 2. New Pi Deploy page
- Added a dedicated **Pi Deploy** page in the GUI.
- This page builds a `pi_bundle/` folder from an exported `.tflite` model.
- Bundle includes:
  - model
  - labels
  - config JSON
  - Pi runtime inference script
  - Pi benchmark script
  - Pi requirements file
  - Pi README

### 3. Pi runtime scripts included
- Added `run_tflite_detect.py` for Raspberry Pi image/video/camera inference.
- Added `benchmark_tflite.py` to estimate Pi-side inference speed.
- Runtime tries `tflite-runtime` first, then falls back to `tensorflow.lite.Interpreter`.

### 4. Documentation update
- README now documents the **PC-train / Pi-run** workflow.
- Added notes about real-world Pi compatibility limits and testing expectations.

## Why this change matters
Before this patch, the app could train and export, but it did not provide a clean deployment path for Raspberry Pi.
Now the workflow is much closer to your real target:

**Train on PC -> Export TFLite -> Package Pi bundle -> Copy to Pi -> Run and benchmark**

## Recommended export path
For the first working Pi model:
- model: small YOLO variant
- format: `tflite`
- size: `320`
- quantization: `int8`

Fallback:
- quantization: `float16`

## Remaining limitations
- Actual Pi success still depends on the Pi runtime environment.
- Some exported models may still need tuning for speed or supported ops.
- The runtime script is a practical draft and may need small adjustments once matched to your exact exported model output format.
- This patch does not yet perform one-click deployment into your PiServer project tree.

## Next recommended step
Use this updated trainer to produce one small TFLite detector for:
- `he3`
- `mineral`
- `radiation`
- optional zone labels

Then test the generated `pi_bundle` directly on the Pi before integrating it into the full CustomDrive mission loop.
