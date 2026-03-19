# CustomTrainer

CustomTrainer is a PySide6 desktop workflow for YOLO-based dataset labeling, training, validation, export, and Raspberry Pi deployment preparation.

## Core workflow tabs

- **Marking** — session browsing, box editing, class management, YOLO label save.
- **Training** — Ultralytics training jobs with device selection and controls.
- **Validation** — validation + prediction runs and preview review.
- **Export** — weight export to deployment formats.
- **Pi Deploy** — Pi-oriented helper utilities and runtime artifact guidance.

## Project layout

```text
CustomTrainer/
├── run_custom_trainer.py
├── requirements.txt
├── custom_trainer/
│   ├── app.py
│   ├── state.py
│   ├── services/
│   ├── ui/
│   ├── utils/
│   └── assets/pi_runtime/
└── PATCH_NOTES/
```

## Prerequisites

- Python 3.11 recommended.
- Desktop GUI environment.
- Compatible PyTorch/Ultralytics stack for training and validation operations.

## Install and run

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

## Marking tab guide

1. Select a **sessions root folder**.
2. Let the app scan and list discovered sessions.
3. Open a session and choose an image.
4. Draw/edit YOLO boxes.
5. Save labels and maintain `classes.txt`.

### Marking productivity shortcuts

- Multi-select frames: `Ctrl + Click`
- Delete selected frames: `X`
- Move selected box: arrow keys
- Previous/next frame: `A` / `D`

### Label path handling

Canonical structure:

- images: `session/images/*.jpg`
- labels: `session/labels/*.txt`

The scanner can auto-repair older misplaced label layouts into canonical YOLO paths.

## Training tab guide

- Launch Ultralytics training directly from GUI.
- Fill defaults from current sessions root.
- Choose device: **Auto**, **CUDA**, or **CPU**.
- Use **Stop Training** to terminate running jobs.

## Validation tab guide

- Run validation from GUI.
- Run prediction on selected source.
- Preview updates to model-rendered boxed output after prediction.
- Use **Use Latest best.pt** to quickly target newest checkpoint.
- Use **Stop Task** for cancellation.

## Export tab guide

- Export to `TFLite`, `ONNX`, `OpenVINO`, or `TorchScript`.
- Choose precision format (INT8 / float16 / float32 when available).
- Use **Use Latest best.pt** for convenience.
- Use **Stop Export** to cancel active export task.

## Architecture notes

- Training/validation/export run through internal Python service wrappers.
- No external `yolo` shell command is required.
- Validation prediction outputs are session-oriented and preview-aware.

## Pi deployment notes

See:

- `custom_trainer/assets/pi_runtime/README_PI.md`

That guide covers running exported TFLite detector artifacts on Raspberry Pi.

## Version highlights

### `0_1_12`

- Consolidated around a single session-based Marking workflow.
- Added/expanded training, validation, and export workflow pages.
- Continued alignment with piTrainer desktop-shell architecture.
