# CustomTrainer 0_1_3

CustomTrainer now keeps the **single session-based Marking tab** from 0_1_2 and restores the extra workflow pages you asked for:

- **Marking**
- **Training**
- **Validation**
- **Export**

The app still follows the PySide6 desktop-shell direction of piTrainer, but the labeling workflow stays focused on **one main Marking page** that loads all sessions from a chosen root folder.

## Main workflow

1. Open **Marking**
2. Choose the folder that contains all your sessions
3. The app scans and lists every session it finds
4. Pick a session, then pick an image
5. Draw / edit YOLO boxes and save labels
6. Move to **Training**, **Validation**, or **Export** when needed

## Marking page features

- scan a sessions root folder
- load and list all sessions in that folder
- load images from the selected session
- label images in one marking tab
- save YOLO `.txt` files
- edit and save `classes.txt`
- keyboard shortcuts for save / image navigation / box editing

## Restored tabs

### Training
- start an Ultralytics YOLO training run from the GUI
- fill defaults from the current sessions root

### Validation
- run YOLO validation from the GUI
- run prediction on a selected source
- fill defaults from the current sessions root and currently selected image

### Export
- export weights to TFLite / ONNX / OpenVINO / TorchScript
- INT8 / float16 / float32 choices
- fill dataset.yaml from the current sessions root

## Install

```bash
python -m venv .venv

# Windows
.venv\Scriptsctivate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python run_custom_trainer.py
```

## Shortcuts

- `Ctrl+1..Ctrl+4` switch tabs
- `Ctrl+S` save current labels on Marking
- `PageUp / PageDown` previous / next image on Marking
- `Delete` delete selected box
- `Arrow keys` move selected box
- `Shift + Arrow keys` move selected box faster
- `F1` show shortcuts

## Notes

- Training / Validation / Export use **Ultralytics** through an internal Python runner module, so they do not depend on the external `yolo` shell command.
- You still need a valid `dataset.yaml` and model weights for training, validation, and export.
