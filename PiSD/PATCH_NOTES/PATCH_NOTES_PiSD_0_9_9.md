# PiSD 0.9.9 Patch Notes — AI Runtime Install Guidance

## Request summary

Some Raspberry Pi installs showed AI Mode diagnostics like:

```text
Runtime: TFLite missing / Keras missing
Backend: load_failed
Failed to load AI model: TFLite runtime is not installed...
```

The uploaded model file was visible to PiSD, but the Pi could not import any runnable `.tflite` backend.

## Cause

PiSD model discovery only checks whether model files exist in `PiSD/models/`. Running a `.tflite` model also requires a Python runtime package in the same Python environment that starts PiSD.

On affected Pis, all three backend imports failed:

- `tflite_runtime.interpreter`
- `ai_edge_litert.interpreter`
- `tensorflow`

So AI Mode correctly refused to run the model, but the page did not give a clear copy/paste repair path.

## Files changed

- `pisd/services/ai_drive_service.py`
- `pisd/web/templates/ai_mode.html`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/css/ai_mode.css`
- `scripts/install_ai_runtime.py`
- `scripts/check_ai_runtime.py`
- `scripts/test_ai_drive_service.py`
- `scripts/test_ai_mode_page.py`
- `docs/AI_RUNTIME_SETUP.md`
- `README.md`
- `requirements.txt`
- `pisd/__init__.py`

## Behaviour changed

- AI runtime diagnostics now include:
  - Python executable path
  - recommended runtime package
  - fallback runtime package
  - copy/paste install commands
  - runtime check command
- AI Mode now shows a **TFLite install help** box when `Runtime` reports `TFLite missing`.
- The load failure text now gives the exact helper command:

```bash
cd ~/PiDrive/PiSD
python3 scripts/install_ai_runtime.py --runtime tflite-runtime
python3 scripts/check_ai_runtime.py
```

- Added a fallback helper path:

```bash
python3 scripts/install_ai_runtime.py --runtime ai-edge-litert
python3 scripts/check_ai_runtime.py
```

- Added `scripts/check_ai_runtime.py` so the user can confirm whether the current Python environment can import a TFLite backend before restarting PiSD.
- Added `scripts/install_ai_runtime.py` so the runtime installation command is consistent across Pis.
- README and `docs/AI_RUNTIME_SETUP.md` now document the missing-runtime case.

## Compatibility notes

- This patch does not auto-install packages from the web during PiSD startup.
- It does not change model inference logic, motor output logic, keyboard steering, overlay settings, recording data, or safety gating.
- `requirements.txt` does not force-install `tflite-runtime` by default because AI runtime wheel availability depends on Pi OS, CPU architecture, and Python version. The helper script should be run on each Pi that reports missing runtime.

## Verification actually performed

Applied on top of the current `0.9.8` patch chain and ran:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_drive_service.py
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
python3 scripts/check_ai_runtime.py
```

Expected local note: the container environment does not have `tflite_runtime`, `ai_edge_litert`, or `tensorflow`, so `check_ai_runtime.py` correctly reported missing runtime in this environment.

## Hardware/model testing

- Real Raspberry Pi package installation was not run here.
- Real `.tflite` inference was not run here.
- Camera and motor hardware tests were not run here.

## Next steps

On any Pi showing `TFLite missing`, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/install_ai_runtime.py --runtime tflite-runtime
python3 scripts/check_ai_runtime.py
sudo systemctl restart pisd.service
```

If `tflite-runtime` is unavailable, try:

```bash
python3 scripts/install_ai_runtime.py --runtime ai-edge-litert
python3 scripts/check_ai_runtime.py
sudo systemctl restart pisd.service
```
