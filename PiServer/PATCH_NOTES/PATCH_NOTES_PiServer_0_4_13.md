# PATCH NOTES — PiServer_0_4_13

## Request summary
Implement PiDrive engineering roadmap **U12**: detect TensorFlow Lite model input
shape and dtype from the model interpreter instead of resizing every camera
frame to the old fixed 200x112 size. Validate incompatible model signatures
before activating them; show the actual dimensions when a model loads.

## Baseline and anti-rollback
- Stable PiServer baseline: `PiServer_0_4_0`; this update continues the `0_4_x` patch line.
- **Stacked on draft PR #14 (0_4_12)**, itself stacked on PR #9 (0_4_11).
- Reviewed 0_4_12, 0_4_11, 0_4_10 and 0_4_9 notes and the current model service.
- Preserves 0_4_12 LAN authentication, browser CSRF/token login, 0_4_11 manual
  command watchdog/e-stop changes, camera AWB defaults, layout keys and settings.

## Root cause
The original `ModelService._prepare_input` always converted camera frames to
200x112 RGB float32 regardless of the loaded TFLite input tensor. piTrainer
exports CNN models with configurable input dimensions (160x120 by default),
so `set_tensor` could fail at inference time without a clear load-time error.
There was also no load-time check for output shape/quantization or non-finite
model outputs.

## Files changed
- `PiServer/piserver/services/model_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/tests/test_model_compatibility.py` (new)
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_13.md` (new)

## Exact behavior changed
1. A candidate TFLite interpreter is allocated and inspected before activation.
   One fixed NHWC RGB input tensor `[1, height, width, 3]` is required.
   The inferred width/height drive camera-frame resize; no hardcoded model size.
   A 4096x4096-pixel safety ceiling rejects unreasonably large allocations.
2. One output tensor containing exactly two values in order
   `[steering, throttle]` is required, matching the current piTrainer TFLite
   export wrapper. Invalid output shapes, multiple inputs/outputs, and
   unsupported input/output dtypes are rejected with explicit errors.
3. Float32, uint8 and int8 inputs/outputs are supported with validated
   quantization scales. Quantization rounds to the nearest integer before
   clipping to the dtype range (avoids float rounding truncation artifacts).
4. A synthetic zero-input inference preflight must complete with two finite
   output values before the candidate can replace a previously working model.
   Failed loads leave the previous active interpreter, model name, and input
   dimensions unchanged.
5. Runtime non-finite outputs cause prediction to return None instead of
   producing saturated motor commands. Existing steering [-1,1] and throttle
   [0,1] clamps are preserved for finite outputs.
6. The `/api/model/list` and `/api/model/load` JSON responses expose the
   active model's `input_spec` with width, height, channels and dtype; the
   model-load banner shows the resolved shape. Existing response keys remain.
7. Inference and active interpreter/shape selection are protected by the
   existing model lock. Deleting an active model clears its cached tensor
   metadata. `APP_VERSION` becomes `0_4_13` for browser cache busting.

## Verification actually performed
Tests run against the uploaded PiServer code whose `model_service.py` and
`tests/test_model_service.py` Git blob SHA values match the live PR #14 branch:
- `python -m unittest discover -s tests -p 'test_model_compatibility.py' -v`
  -> **9 tests passed** with fake TFLite interpreters.
- `python -m unittest discover -s tests -q` -> **44 tests passed**
  in the local repository checkout (includes the nine new tests).
- `python -m compileall -q piserver tests` -> passed.
- `node --check piserver/web/static/app.js` -> passed on locally
  modified JS using the identical model-banner edit.
- Exact uploaded Git blobs for model service and test file were compared
  with the tested local file hashes. Existing 0_4_12 JS auth/CSRF and app
  registration were checked for preservation.

## Known limitations / follow-up
- These are mock-interpreter tests; TensorFlow Lite runtime and physical
  Raspberry Pi camera/motor tests were **not** performed. Run those on the Pi
  with wheels raised before merging or deploying.
- Real models with more than one input/output, non-RGB inputs, non-single-batch
  shapes or unrecognized quantized tensors are explicitly unsupported.
- This patch does not implement model metadata sidecars (U27), model-upload
  file signing, new AI steering logic, a motor hardware watchdog, or generic
  dynamic resize for `shape_signature` inputs.
- The stacked PR depends on PR #14, which depends on PR #9; merge in order.
