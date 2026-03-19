# PiDrive

PiDrive is a single repository that contains multiple PiCar-related apps and utilities. Each project can be run independently, but they are designed to work together as a complete data collection, training, and deployment workflow.

## What is in this repo

- **`piCar_0_3_2/`** — legacy Flask runtime for manual driving, recording, and inference.
- **`PiServer/`** — modular runtime with services for camera, motor, algorithms, recording, and web control.
- **`piTrainer/`** — PySide6 desktop app for steering/throttle dataset curation and model training/export.
- **`CustomTrainer/`** — PySide6 YOLO labeling/training/validation/export workflow with Pi runtime helpers.
- **`CustomDrive/`** — mission-controller scaffold for autonomous competition-style routines (sim + live modes).

## Repository layout

```text
PiDrive/
├── README.md
├── INSTRUCTIONS.md
├── piCar_0_3_2/
├── PiServer/
├── piTrainer/
├── CustomTrainer/
└── CustomDrive/
```

## End-to-end workflow (recommended)

1. **Collect driving data** with `piCar_0_3_2` or `PiServer` recording.
2. **Train driving model** in `piTrainer` (steering/throttle).
3. **Train object model** in `CustomTrainer` if your mission needs detection.
4. **Deploy and run** on Pi with `PiServer` (manual/auto runtime).
5. **Run mission logic** through `CustomDrive` for route/state-machine orchestration.

## Prerequisites

- Python **3.11** recommended across projects.
- `pip` and `venv` available.
- Raspberry Pi-specific packages (`picamera2`, `RPi.GPIO`, `tflite-runtime`) only required for live Pi hardware features.

## Quick start by project

### 1) `piCar_0_3_2` (legacy runtime)

```bash
cd piCar_0_3_2
python server.py
```

Use this for historical compatibility or older workflows.

### 2) `PiServer` (modular runtime)

```bash
cd PiServer
python -m pip install -r requirements.txt
python server.py
```

Open `http://<pi-ip>:5000` from a browser on the same network.

### 3) `piTrainer` (driving model trainer)

```bash
cd piTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 4) `CustomTrainer` (YOLO workflow)

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

### 5) `CustomDrive` (mission scaffold)

```bash
cd CustomDrive
python run_custom_drive_demo.py
```

## Documentation index

- Repository maintenance and contribution workflow: `INSTRUCTIONS.md`
- PiServer runtime setup and configuration: `PiServer/README.md`
- piTrainer setup and usage: `piTrainer/README.md`
- piTrainer package internals: `piTrainer/piTrainer/README.md`
- CustomTrainer setup and workflow: `CustomTrainer/README.md`
- Pi-side runtime bundle for detector inference: `CustomTrainer/custom_trainer/assets/pi_runtime/README_PI.md`
- CustomDrive launch/configuration details: `CustomDrive/README.md`

## Troubleshooting quick tips

- If a GUI app does not start, confirm your virtual environment is active and dependencies were installed for that environment.
- If Pi camera preview is blank, verify Pi camera stack (`libcamera`/`picamera2`) and permissions.
- If motor output is not active, check whether runtime is in simulated fallback mode and whether GPIO dependencies are installed.
- If training pages fail, verify TensorFlow / Ultralytics dependencies match your Python version.
