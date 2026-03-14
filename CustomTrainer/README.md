# CustomTrainer 0_1_11

CustomTrainer keeps the **single session-based Marking tab** and the extra workflow pages:

- **Marking**
- **Training**
- **Validation**
- **Export**

The app follows the PySide6 desktop-shell direction of piTrainer, while the labeling workflow stays focused on one main Marking page that loads all sessions from a chosen root folder.

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
- multi-select frames in the frame list with `Ctrl + Click`
- delete selected frame(s) with `X`
- move selected box with arrow keys
- change frames with `A / D`

## Training / Validation / Export

### Training
- start an Ultralytics YOLO training run from the GUI
- fill defaults from the current sessions root
- device picker supports **Auto / CUDA / CPU** detection
- current frame preview mirrored from the Marking workflow
- **Stop Training** button

### Validation
- run YOLO validation from the GUI
- run prediction on a selected source
- frame preview for the current validation / prediction image
- **Use Latest best.pt** button
- **Stop Task** button

### Export
- export weights to TFLite / ONNX / OpenVINO / TorchScript
- INT8 / float16 / float32 choices
- **Use Latest best.pt** button
- **Stop Export** button

## Install

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python run_custom_trainer.py
```

## GPU notes

- The app can auto-detect runtime devices and pass the correct device into Ultralytics.
- **Auto** chooses the best available backend in this order: CUDA GPU, Apple MPS, then CPU.
- If you explicitly request CUDA but your environment only has a CPU build of PyTorch, the app will show a clear error instead of silently falling back.
- To actually train on an NVIDIA GPU, your Python environment must use a CUDA-enabled PyTorch build.

## Shortcuts

- `Ctrl+1..Ctrl+4` switch tabs
- `Ctrl+S` save current labels on Marking
- `PageUp / PageDown` previous / next image
- `Arrow keys` move selected box
- `Shift + Arrow keys` move selected box faster
- `A / D` previous / next frame on the image canvas
- `X` delete selected frame(s)
- `Backspace / Delete` delete selected box
- `F1` show shortcuts

## Notes

- Training / Validation / Export use Ultralytics through an internal Python runner module, so they do not depend on the external `yolo` shell command.
- Single-session folders such as `session/images/*.jpg` save labels to `session/labels/*.txt`.
- Older misplaced labels under `session/images/labels/*.txt` or `session/labels/images/*.txt` are auto-repaired into the canonical YOLO path when sessions are scanned.
