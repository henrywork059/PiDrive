# PiDrive

PiDrive is a monorepo that contains multiple PiCar-related applications:

- **`piCar_0_3_2/`**: Legacy Flask runtime for manual driving, recording, and model inference.
- **`PiServer/`**: Modular Flask runtime (`piserver`) with services/algorithms/web workspace architecture.
- **`piTrainer/`**: PySide6 desktop trainer for steering/throttle datasets and model export.
- **`CustomTrainer/`**: PySide6 desktop YOLO workflow for marking, train/validate/export, and Pi deployment helpers.
- **`CustomDrive/`**: Mission-controller scaffold and simulation demo for competition-style autonomous tasks.

The repository also stores per-project patch notes (`*/PATCH_NOTES/`) and some exported session archives (`*.zip`) in the root.

## Repository layout

```text
PiDrive/
├── README.md
├── INSTRUCTIONS.md
├── piCar_0_3_2/          # legacy runtime
├── PiServer/             # modular runtime
├── piTrainer/            # steering/throttle trainer
├── CustomTrainer/        # YOLO trainer + deploy
└── CustomDrive/          # mission state machine scaffold
```

## Quick start

### piCar_0_3_2 (legacy runtime)

```bash
cd piCar_0_3_2
python server.py
```

### PiServer (modular runtime)

```bash
cd PiServer
python -m pip install -r requirements.txt
python server.py
```

### piTrainer (desktop trainer)

```bash
cd piTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### CustomTrainer (desktop YOLO workflow)

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

### CustomDrive demo

```bash
cd CustomDrive
python run_custom_drive_demo.py
```

## Documentation index

- Repository maintenance guidance: `INSTRUCTIONS.md`
- Legacy runtime notes: `piCar_0_3_2/PATCH_NOTES/`
- PiServer usage/config: `PiServer/README.md`
- piTrainer setup/features: `piTrainer/README.md`
- CustomTrainer workflow: `CustomTrainer/README.md`
- CustomDrive mission scaffold: `CustomDrive/README.md`
