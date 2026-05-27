# PiSD 0.9.4 Patch Notes — AI model load diagnostics and TFLite backend visibility

## Request summary

The user reported that a piTrainer-exported `.tflite` model still showed as selected but not runnable in AI Mode. The UI showed the model file in `PiSD/models/`, but AI Mode still reported:

```text
AI mode cannot start because no runnable model is loaded.
```

The screenshot also showed:

```text
Backend: selected
Outputs: -
piTrainer export: not loaded
model_loaded: false
model_ready: false
```

## Cause / root cause

The model file was being selected, but the load attempt was not becoming a runnable backend. When a `.tflite` load failed, PiSD left the backend state as `selected`, and a later Start AI attempt could overwrite the more useful load failure with the generic `PISD-AI-003` not-loaded warning.

This made it hard to see whether the actual issue was:

- no TFLite runtime installed in the PiSD Python environment;
- a model file that the runtime could not open;
- a supported file extension but unsupported runtime backend;
- a model selected but not successfully loaded.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/scripts/test_ai_drive_service.py`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_4.md`

## Behaviour changed

### AI backend status is clearer

Failed model loads now show:

```text
Backend: load_failed
```

instead of staying at the ambiguous:

```text
Backend: selected
```

The selected model ID/path is still kept, so the user can fix the runtime dependency and click **Load model** again without re-uploading the model.

### Runtime diagnostics added

AI status now includes:

```json
"runtime_support": {
  "tflite_runtime": true/false,
  "ai_edge_litert": true/false,
  "tensorflow": true/false,
  "tflite": true/false,
  "keras": true/false
}
```

The **Load trained model** panel now shows a new Runtime field, for example:

```text
TFLite missing / Keras missing
```

or:

```text
TFLite OK / Keras missing
```

### Last load/error field added

The AI model panel now shows a **Last load/error** readout so the root model load failure is visible without needing to scroll through the full AI log JSON.

### TFLite backend import order expanded

For `.tflite` models, PiSD now tries these Python interpreter backends in order:

```text
tflite_runtime.interpreter
ai_edge_litert.interpreter
tensorflow.lite.Interpreter
```

If none is available, the load failure message includes the import attempts and the runtime diagnostics.

### Start / Predict no longer hide the real load error

When the user clicks **Start AI preview**, **Start AI drive**, or **Predict once** while a model is selected but not ready, PiSD now tries to load the selected model first. If loading fails, it returns the model load failure directly instead of replacing it with the generic no-runnable-model message.

## Behaviour preserved / rollback check

Before finalising, this patch was checked against the latest patch notes:

- `0_9_3`: piTrainer model upload/delete and output parsing are preserved.
- `0_9_2`: keyboard steering ramp timing remains `0.8 s`.
- `0_9_1`: Manual Drive motor start dead-zone popup and keyboard release-to-centre are preserved.
- `0_9_0`: v9 stable package behaviour, linear X steering, and keyboard throttle/Space controls are preserved.

Confirmed this patch does not restore:

- `turn_gain` in real motor steering;
- motor `turn_curve` in real motor steering;
- Manual Drive steer strength;
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

Observed results:

- AI service test now confirms runtime diagnostics are exposed.
- AI service test now confirms failed model loading reports `backend = load_failed` and keeps runtime diagnostics.
- AI Mode static test confirms the Runtime and Last load/error UI fields are present.
- Existing Manual Drive keyboard/dead-zone checks still pass.
- Existing linear steering and settings persistence checks still pass.

## Verification not performed / known limits

- Real `.tflite` inference was not run here because this container does not include a TFLite runtime backend.
- Real browser route testing was not run here because Flask is not installed in this container.
- Hardware camera/motor testing was not run here.

## Suggested Pi-side check after applying

1. Restart PiSD after applying the patch.
2. Open `/ai-mode`.
3. Select `picar_model.tflite`.
4. Click **Load model**.
5. Read the new **Runtime** and **Last load/error** fields.

If Runtime says `TFLite missing`, install a compatible TFLite backend in the same Python environment used to run PiSD, restart PiSD, then click **Load model** again.
