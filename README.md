# PiDrive

PiDrive is a two-part project for autonomous RC car workflows:

- **`piCar_0_3_2/`**: Runtime driving stack (Flask web control server, camera stream, control API, recording, model loading/inference).
- **`piTrainer/`**: Desktop training tool (PySide6 app for dataset management, preprocessing, training, validation, and export).

This repository also includes historical patch notes and sample recording archives (`*.zip`) at the root.

## Repository layout

```text
PiDrive/
├── README.md
├── INSTRUCTIONS.md
├── piCar_0_3_2/
│   ├── server.py
│   ├── control_api.py
│   ├── camera.py
│   ├── model_manager.py
│   ├── autopilot.py
│   ├── data_recorder.py
│   ├── PATCH_NOTES/
│   └── ...
└── piTrainer/
    ├── main.py
    ├── requirements.txt
    ├── README.md
    ├── piTrainer/
    │   ├── app.py
    │   ├── app_state.py
    │   ├── pages/
    │   ├── panels/
    │   ├── services/
    │   ├── ui/
    │   └── utils/
    └── PATCH_NOTES/
```

## Quick start

### 1) PiCar runtime (`piCar_0_3_2`)

Run the Flask server on the target device:

```bash
cd piCar_0_3_2
python server.py
```

The UI and APIs are hosted from the same app (default: `http://0.0.0.0:5000`).

### 2) Training desktop app (`piTrainer`)

For full training instructions, see `piTrainer/README.md`.

Typical run flow:

```bash
cd piTrainer
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python main.py
```

## Data and model flow (high level)

1. Drive and record sessions from the PiCar web UI.
2. Use `piTrainer` to load session data and inspect/clean/filter frames.
3. Preprocess and train steering/throttle models.
4. Export `.keras` / `.tflite` models.
5. Upload and load models back into PiCar runtime.

## Development notes

- Keep runtime and trainer concerns separate (`piCar_0_3_2` vs `piTrainer`).
- Preserve current behavior for control, recording, and model inference paths.
- Prefer additive documentation and non-behavioral cleanup unless a functional change is explicitly requested.
- Version history is maintained under each module’s `PATCH_NOTES/` directory.

## Documentation index

- Root usage and structure: `README.md` (this file)
- Maintenance and non-functional cleanup guidance: `INSTRUCTIONS.md`
- Trainer-specific setup and feature details: `piTrainer/README.md`
