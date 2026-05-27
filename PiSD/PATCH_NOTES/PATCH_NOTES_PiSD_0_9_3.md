# PiSD 0.9.3 Patch Notes — piTrainer model compatibility and AI model upload/delete

## Request summary

The user asked to update AI Mode so PiSD can run the AI model trained and exported from piTrainer. The user also asked for the **Load trained model** panel to include:

- an upload button so a model can be uploaded from the browser to the Pi;
- a delete button so a selected model can be removed from the Pi.

## Cause / root cause

PiSD AI Mode already listed and loaded model files from `PiSD/models/`, but the runtime parser assumed a simple flattened model output. Current piTrainer CNNs export two named outputs, `steering` and `throttle`, and depending on the saved/exported format the inference backend may return one of several shapes:

- Keras dict output: `{steering: ..., throttle: ...}`;
- Keras list/tuple output with output names;
- one two-value tensor `[steering, throttle]`;
- TFLite two-output tensors, normally with output names that include steering/throttle.

The AI Mode page also required users to manually copy files into `PiSD/models/`; it did not provide browser upload/delete actions.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/scripts/test_ai_drive_service.py`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_3.md`

## Behaviour changed

### piTrainer export compatibility

AI Mode now parses piTrainer-style model outputs more safely.

Supported prediction output forms now include:

```text
{"steering": value, "throttle": value}
[steering_tensor, throttle_tensor] with output names
[[steering, throttle]]
[steering, throttle]
```

For TFLite models, PiSD now reads all output tensors instead of only the first output tensor. It then maps named outputs containing `steer` to steering and outputs containing `throttle`/`throt` to throttle. If a model exposes a single two-value tensor, PiSD uses index 0 as steering and index 1 as throttle.

For `.keras` / `.h5` models, PiSD now accepts Keras dict/list/two-value prediction outputs.

### TFLite input handling

TFLite input conversion now handles float, uint8, and quantized integer input tensors more carefully:

- float inputs receive normalized image data in `0.0..1.0`;
- quantized integer inputs use the tensor quantization scale/zero-point when present;
- uint8 inputs without quantization metadata fall back to `0..255` conversion.

### AI Mode upload button

The **Load trained model** panel now has:

```text
Upload model to Pi
Upload model
```

The upload endpoint is:

```text
POST /api/ai/upload-model
```

Uploaded files are saved into:

```text
PiSD/models/
```

The filename is sanitized. If a file with the same name already exists, PiSD appends a timestamp instead of silently overwriting the older model.

### AI Mode delete button

The **Load trained model** panel now has:

```text
Delete selected
```

The delete endpoint is:

```text
POST /api/ai/delete-model
```

Deletion is limited to safe model IDs inside `PiSD/models/`. If the deleted model was currently selected/loaded, PiSD unloads it and clears the saved selected model ID.

### UI/status changes

The model panel now also shows:

- loaded backend;
- input shape;
- output names;
- models folder;
- whether the currently loaded backend is a piTrainer-compatible runtime path.

## Behaviour preserved / rollback check

Before finalising, the current code and recent patch notes were checked against:

- `0_9_2`: keyboard steering ramp timing is still `0.8 s` for hold and release-to-centre;
- `0_9_1`: Motor start dead-zone popup and release-to-centre behaviour are not removed;
- `0_9_0`: keyboard throttle steps, Space stop, linear X steering, and v9 stable package structure are preserved;
- `0_8_11`: overlay settings sidecar files for recording/snapshot reuse are preserved.

Confirmed this patch does not restore:

- `turn_gain` in real motor steering;
- motor `turn_curve` in real motor steering;
- Manual Drive `steer_strength`;
- old Motor Tuning panels;
- capped Manual visual tuning overlay values.

## Verification actually performed

Performed locally from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_drive_service.py
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

The checks passed in this local static/simulation environment.

`test_ai_drive_service.py` now also checks:

- safe model upload filename handling;
- model delete handling;
- piTrainer-style dict/list/two-value output parsing.

## Not verified here

- Real browser upload/delete against a running Flask app was not tested here because this container environment does not include Flask for full route testing.
- Real TensorFlow / TensorFlow Lite inference on a piTrainer exported model was not run here because this container does not include those runtimes.
- Hardware camera/motor testing was not run here.

## Pi-side test suggestion

1. Export a `.tflite` model from piTrainer if possible. Use `.keras` only if TensorFlow is installed on the Pi.
2. Open PiSD `/ai-mode`.
3. In **Load trained model**, choose the exported file and click **Upload model**.
4. Click **Refresh models** if needed, then select the uploaded model.
5. Click **Load model**.
6. Start camera/live preview.
7. Use **Predict once** or **Start AI preview** before enabling AI drive.
8. Only use **Start AI drive** with the wheels lifted and safety checkbox enabled.
