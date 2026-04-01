# CustomTrainer

CustomTrainer is a PySide6 desktop workflow for YOLO-style labeling, training, validation, export, and Pi-focused deployment prep.

## Core tabs

- **Marking** — browse sessions, edit boxes, maintain `classes.txt`, save YOLO labels
- **Training** — launch Ultralytics training jobs from the GUI
- **Validation** — run validation or prediction and visually inspect saved prediction frames
- **Export Validate** — run validation or prediction against exported models such as `.tflite` / `.onnx`
- **Export** — export trained weights to Pi-friendly formats

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

## What changed in 0_2_9

- keeps the startup-safe device probing, dataset export / preflight fixes, fast Marking shortcuts, and top-level-only frame scanning from 0_2_8
- adds a new **Export Validate** tab for checking exported models such as `.tflite` and `.onnx`
- lets you run exported-model validation for metrics or exported-model prediction for saved preview frames
- can auto-pick the latest exported model found under the current sessions root
- keeps the regular **Validation** tab focused on `best.pt` / training-side checks
- updates the visible main window version to 0_2_9

## Main workflow

1. Open **Marking**
2. Choose the root folder that contains your sessions
3. Label frames and save YOLO labels
4. Open **Training** to train from the current sessions root
5. Use **Marking → Quick Deploy Current Frame** to run quick prediction on the active frame with the latest `best.pt`, then refine the loaded predicted boxes directly in the main Marking canvas
6. Open **Export** to export the newest trained weights
7. Open **Export Validate** to test the exported `.tflite` / `.onnx` model on the same frames

## Marking page highlights

- scans a sessions root folder and lists discovered sessions
- automatically reloads the last valid sessions root at startup
- supports draggable split panels for session source / sessions / images / canvas / tools
- supports multi-select frames with `Ctrl + Click`
- uses `A / D` for previous / next frame and auto-saves the current labels before switching
- lets you right-click a box to select it and right-drag the selected box to reposition it
- uses `W / S` to cycle the selected box class or the active class for new boxes
- uses `Delete` to remove the selected box
- uses `X` to delete selected frame(s)
- uses arrow keys to move the selected box
- draws each class with its own box color
- includes a single Quick Deploy button on Marking for fast prediction on the current frame
- can load quick-deploy predicted boxes into the main annotation canvas so you can correct and save them as labels

## Training page highlights

- launches training through the internal Python runner, not an external `yolo` shell command
- can auto-create `dataset.yaml` from the current sessions root when needed
- includes a dedicated **Run Log**
- includes a live **Training Progress Plot** sourced from `results.csv`
- keeps a mirrored frame preview from the Marking workflow
- focuses on training configuration, run logs, and live metric plots while quick deploy now lives on Marking

## Validation page highlights

- can run pure validation with metrics output
- can run prediction on a single file **or a folder of frames**
- saves model-rendered prediction frames and lets you browse them with **Prev / Next Frame**
- supports output styling controls for predicted boxes and labels
- includes a dedicated **Run Log**

## Export Validate page highlights

- can run validation on exported models such as **TFLite** or **ONNX**
- can run exported-model prediction on a single file **or a folder of frames**
- saves exported-model prediction frames and lets you browse them with **Prev / Next Frame**
- can auto-pick the latest exported model from the current sessions root
- includes a dedicated **Run Log**

## Export page highlights

- exports to **TFLite**, **ONNX**, **OpenVINO**, or **TorchScript**
- supports **INT8 / float16 / float32** export choices
- can auto-pick the latest `best.pt`
- includes a dedicated **Run Log**

## Install and run

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

## Notes

- Training, validation, prediction, exported-model validation, and export run through internal Python service wrappers.
- Validation prediction on folders is useful for visually checking model performance across all session frames.
- Export Validate gives you a similar review flow for exported models like `.tflite` and `.onnx`.
- Screen-aware startup sizing keeps the main window inside the available desktop area on smaller displays.
- UI state is stored locally so the app can remember the last sessions root and splitter positions.

See `custom_trainer/assets/pi_runtime/README_PI.md` for Pi-side TFLite runtime notes.
