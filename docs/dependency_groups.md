# Active dependency audit — F9 (Batch 3 candidate)

Baseline 8c979f3; R53 parent d2020825. Inspected actual launchers and camera/motor/AI, trainer app/window and model train/export/validation modules. Scope only active components.

| Component | Core/full | Optional hardware or reduced mode | Development |
| --- | --- | --- | --- |
| PiSD | PiSD/requirements.txt (Flask, existing utilities, NumPy/Pillow/OpenCV) | requirements-pi.txt alternative GPIO; OS Picamera2/libcamera; separate existing TFLite/LiteRT installer | requirements-dev.txt |
| PiServer | PiServer/requirements.txt (Flask, NumPy/OpenCV) | requirements-pi.txt alternative GPIO; OS Picamera2; optional tflite_runtime or TensorFlow fallback | requirements-dev.txt |
| piTrainer | piTrainer/requirements.txt (desktop + TensorFlow) | requirements-desktop.txt for data review only | requirements-dev.txt |

PiSD retains non-hardware utility declarations conservatively; audit actual imports throughout the codebase before pruning. TensorFlow remains part of the default trainer workflow. CI validates declared full/core files in new Python 3.11 venvs after the established four-job checks. Device-specific installs, real training, native Windows and desktop-only smoke still require separate verification. No claim of exhaustive dependency audit or accepted releases yet. Avoid unverified system-wide pip changes and never overwrite a newer checkout with historical archives.
