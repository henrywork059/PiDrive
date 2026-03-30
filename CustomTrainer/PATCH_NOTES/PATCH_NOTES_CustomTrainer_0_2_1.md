# PATCH NOTES — CustomTrainer 0_2_1

## Scope
Patch-only update for CustomTrainer based on the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
Fix the startup crash on multiple Windows PCs where `python run_custom_trainer.py` aborted inside `torch_python.dll` before the UI opened.

## Problem addressed
CustomTrainer could crash during startup when the Training, Validation, or Export pages refreshed the available device list and directly probed the local PyTorch/CUDA runtime in the GUI process.

## Likely root cause
- The GUI pages call `refresh_devices()` during page initialization.
- `refresh_devices()` called `probe_runtime()`.
- `probe_runtime()` imported `torch` and queried runtime/device details directly inside the main UI process.
- On the user's affected PCs, that runtime check could abort inside `torch_python.dll`, which terminated the whole application before a normal Python exception could be shown.

## Changes made

### 1) Isolated the runtime probe from the UI process
- Reworked `custom_trainer/services/device_service.py` so runtime probing now happens in a short-lived **subprocess** launched with the current Python executable.
- The subprocess performs the PyTorch import and CUDA/MPS checks, then returns a JSON summary back to the main app.
- If the probe subprocess crashes, times out, exits unexpectedly, or returns invalid data, the main UI stays alive.

### 2) Added safe CPU fallback behavior
- When the isolated runtime probe fails, the app now falls back to a safe device list of:
  - `Auto (best available)`
  - `CPU`
- The UI summary now explains that the probe failed and that Auto will fall back to CPU until the environment is fixed.
- `resolve_device()` now uses the same isolated probe path, so Training / Validation / Export avoid reintroducing the same crash later.

### 3) Updated visible version text
- Updated the main window title to **CustomTrainer 0_2_1** so the visible version label no longer lags behind the delivered patch.
- Updated the README change summary to describe the new startup-safety behavior.

## Files changed
- `CustomTrainer/custom_trainer/services/device_service.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_1.md`

## Verification performed
- Static review of the startup path from Training / Validation / Export page initialization into `probe_runtime()`.
- `python -m compileall custom_trainer run_custom_trainer.py`
- Imported and executed `probe_runtime()`, `runtime_summary()`, and `resolve_device()` in this container to confirm the new fallback path returns structured results without importing Torch in the main process.

## Known limits / next steps
- This patch prevents the GUI from crashing during device probing, but it does **not** repair a broken local Torch/CUDA installation.
- If the runtime probe fails, the app should still open and operate with CPU-safe defaults; GPU use will still depend on the local environment being healthy.
- A later patch could add a dedicated **Device Diagnostics** dialog or a background worker for richer probe details without blocking the UI.
