# PATCH NOTES — CustomTrainer 0_1_8

## Goal
Make CustomTrainer able to run Training / Validation / Export on GPU when a supported runtime is available, while keeping CPU fallback safe and obvious.

## Root issue
The earlier PySide6 rebuild still defaulted the workflow pages to `cpu`, and the device field was only a free-text input. That meant:

- the UI did not actively detect CUDA / MPS availability
- the common path still launched Ultralytics on CPU
- users had no clear runtime feedback about whether their Python environment could actually use GPU
- a CPU-only PyTorch install could be mistaken for a GPU-capable setup

## What changed

### 1) Added runtime device probing
New service:
- `custom_trainer/services/device_service.py`

It now:
- probes PyTorch runtime availability in the GUI process
- detects CUDA GPUs when available
- detects Apple MPS when available
- builds device options for the UI
- resolves `auto` to the best available backend
- raises a clear error if the user explicitly requests CUDA in a CPU-only environment

### 2) Reworked device controls in Training / Validation / Export
Updated pages:
- `custom_trainer/ui/pages/train_page.py`
- `custom_trainer/ui/pages/validate_page.py`
- `custom_trainer/ui/pages/export_page.py`

These pages now:
- use a device combo box instead of a plain text field
- populate device choices from runtime detection
- support `Auto`, detected `CUDA:x`, `MPS`, and `CPU`
- show a runtime summary label
- provide a **Refresh Devices** button

### 3) CLI-side device resolution is now explicit
Updated:
- `custom_trainer/services/ultralytics_cli.py`

The runner now:
- resolves requested device values before calling Ultralytics
- logs both requested and resolved device
- defaults actions to `auto` instead of `cpu`
- surfaces a clearer message when GPU is requested but unavailable

### 4) UI version bump and docs refresh
Updated:
- `custom_trainer/ui/main_window.py`
- `README.md`

Changes:
- window title now shows `CustomTrainer 0_1_8`
- README now includes GPU behavior and runtime notes

## Important limitation
This patch makes the app **GPU-capable**, but it cannot turn a CPU-only PyTorch installation into a CUDA installation.

If the user environment still reports something like:
- `torch ... +cpu`

then Training / Validation / Export will still run on CPU until that environment is switched to a CUDA-enabled PyTorch build.

## Verification
Performed in container:
- syntax compile pass for `custom_trainer/`
- direct test of device probing and `auto` resolution in a CPU-only runtime
- direct test that explicit `cuda` / `cuda:0` requests now raise a clear error on CPU-only runtime

## Changed files in this patch
- `CustomTrainer/custom_trainer/services/device_service.py` *(new)*
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/pages/export_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_8.md`

## Next suggested improvement
Add a small **Runtime Diagnostics** panel that shows:
- torch version
- CUDA available / unavailable
- GPU names
- current resolved device
- quick warning if the environment is CPU-only
