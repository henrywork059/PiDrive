# CustomDrive 0_3_2 Patch Notes

## Request summary
Patch the current CustomDrive GUI AI path so that:
- the TFLite backend stops throwing the interpreter internal-data reference error,
- the live preview stays visually current when overlay is enabled instead of effectively reusing old rendered frames,
- inference is refreshed on a fixed frame cadence instead of trying to run on every preview request,
- and the AI debug window can track backend errors in a copyable log.

The user also asked to check the overlay logic itself and to renew the AI backend if needed so the app is using the current code path rather than accidentally relying on an older call pattern.

## Root cause
There were three linked problems.

### 1) The runtime inference path was still holding interpreter detail objects too close to `invoke()`
The previous code fetched `get_input_details()` and `get_output_details()` inside the hot inference path and then invoked the interpreter while those detail dictionaries were still alive.

On some TensorFlow Lite runtimes, those dictionaries contain NumPy-backed metadata tied to interpreter internals. That can trigger this kind of runtime error:
- `There is at least 1 reference to internal data in the interpreter in the form of a numpy array or slice...`

So the issue was more consistent with interpreter-memory handling than with a missing `.txt` or `.json` sidecar file.

### 2) The overlay path was mixing inference cadence with rendered-frame caching
The previous overlay path could return a cached annotated JPEG for a short time window. That reduced inference load, but it also meant the preview could stop looking like the current live frame whenever overlay was on.

The user explicitly wanted a different behavior:
- keep the preview visually current like the normal camera preview,
- only pass one frame to the model every 5 frames,
- then draw the latest detections onto the following live frames until the next inference refresh.

### 3) The debug UI could freeze a snapshot, but backend error tracking still was not durable enough
`0_3_1` already added snapshot freeze/copy and browser-side snapshot history, but the actual backend error state still changed continuously in normal polling. That made it harder to track repeated runtime faults and compare what the detector/backend was doing across deploy/debug attempts.

## Files changed
- `CustomDrive/custom_drive/tflite_perception.py`
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_2.md`

## Exact behavior changed

### 1) TFLite runtime metadata is now captured once at deploy time
The detector now resolves and stores primitive input/output metadata during model deployment, including:
- input tensor index
- input dtype
- input shape
- selected output tensor index
- selected output shape
- selected output dtype
- selected output quantization scale / zero-point

The hot inference path now uses those copied primitive values instead of repeatedly holding raw interpreter detail dictionaries across `invoke()`.

This is intended to remove the internal-data reference pattern that was producing the new runtime error.

### 2) The inference path now uses the current backend call flow only
The updated `infer_detections()` path now:
- reads cached primitive tensor metadata,
- preprocesses the live frame,
- calls `set_tensor()` / `invoke()` / `get_tensor()` directly,
- copies the output tensor immediately,
- and then parses the copied array.

That keeps the actual active backend path more explicit and avoids leaving the older detail-fetch pattern in the request-time inference loop.

### 3) Overlay now stays visually current while detections refresh every 5 frames
The overlay service no longer returns a cached annotated JPEG as the primary preview throttle.

Instead it now:
- uses the current live frame for drawing every preview request,
- keeps the most recent detection result in memory,
- runs a new inference on the first available frame and then every 5 preview frames after that,
- and draws the latest known detections on the frames in between.

This matches the behavior the user requested more closely:
- current preview stays current,
- model work is throttled,
- overlay boxes persist between inference refreshes.

### 4) Overlay debug text now shows the frame cadence direction
When TFLite overlay is active, the on-frame metadata now also shows the current overlay frame cadence (`every=5f` by default) so it is easier to see which behavior is active while testing.

### 5) AI backend log is now tracked server-side and exposed to the GUI
`ObjectDetectionService` now keeps a rolling backend-side debug/error history.

It records events such as:
- detector deployment
- repeated inference/runtime errors
- JPEG decode failures
- model deletion events

This history is exposed through `ai_status.history` and shown in the AI debug history area in the GUI.

### 6) AI debug history area now combines backend log + snapshot history
The AI debug history text area now shows two sections when available:
- **AI backend log**
- **AI debug snapshots**

This means the user can now copy:
- the backend runtime log entries,
- the frozen/latest snapshot data,
- or both together from the same text area.

### 7) Added backend-log clear route
New route:
- `/api/ai/debug_log/clear`

The existing **Clear History** button now clears the backend log through the server route as well as the browser-side snapshot history.

### 8) GUI asset version bumped forward
The GUI control app version string was updated to `0_3_2` so the browser is more likely to fetch the patched JS/HTML assets immediately after refresh.

### 9) No rollback of the previous arm-speed change
This patch does **not** remove the `0_3_1` arm-speed update.
The prior 2x arm speed behavior remains in place and was intentionally not rolled back while fixing the AI backend.

## Verification actually performed
- Re-read the recent relevant patch notes before patching, especially:
  - `0_2_15`
  - `0_2_16`
  - `0_2_17`
  - `0_3_1`
- Inspected the real uploaded `CustomDrive_0_3_0.zip` baseline and merged the previously produced `0_3_1` patch forward before editing.
- Ran Python syntax checks on:
  - `tflite_perception.py`
  - `object_detection_service.py`
  - `gui_control_app.py`
- Ran:
  - `python -m compileall custom_drive`
- Ran JavaScript syntax check on:
  - `CustomDrive/custom_drive/gui_web/static/app.js`
- Ran parser smoke test for a synthetic `[1,300,6]` tensor in `xyxy + score + class` order and verified it selected `xyxy_score_class` and inferred at least 5 classes.
- Ran a mocked detector smoke test to confirm the updated inference path works from stored tensor metadata without calling interpreter detail APIs inside the hot path.
- Ran a mocked overlay cadence test to confirm the overlay refreshes detections on the initial frame and then on the configured frame interval while still rendering a current output frame every request.

## Known limits / next steps
- I did **not** claim live Pi hardware / live TFLite runtime validation in this container.
- This patch removes the most likely interpreter-reference pattern in the current code, but if the Pi runtime still throws the same error after this patch, the next step should be to inspect the exact installed TFLite runtime build and, if needed, isolate inference into a worker thread/process with a stricter single-owner interpreter lifecycle.
- The overlay cadence is currently code-defaulted to 5 frames. If you want that adjustable from the GUI later, the next patch can expose it as a real AI setting.
