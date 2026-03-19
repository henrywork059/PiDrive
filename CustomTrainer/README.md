# CustomTrainer

CustomTrainer is a PySide6 desktop YOLO workflow with session-based annotation and model lifecycle pages.

## Main tabs

- **Marking**: browse sessions, draw/edit bounding boxes, maintain `classes.txt`, save YOLO labels.
- **Train**: run Ultralytics training jobs with device selection.
- **Validate**: run validation/prediction and review results.
- **Export**: export trained weights (TFLite/ONNX/OpenVINO/TorchScript).
- **Pi Deploy**: deploy-focused utilities for Raspberry Pi runtime artifacts.

## Layout

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
# CustomTrainer 0_1_10

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
- **Run Log** tab on Training for command/runtime output
- training now launches from the CustomTrainer repo root so the internal runner resolves more reliably
- training can auto-create `dataset.yaml` from the currently loaded sessions root when needed

### Validation
- run YOLO validation from the GUI
- run prediction on a selected source
- frame preview for the current validation / prediction image
- prediction preview updates to the model-rendered boxed result after Run Prediction
- **Use Latest best.pt** button
- **Stop Task** button

### Export
- export weights to TFLite / ONNX / OpenVINO / TorchScript
- INT8 / float16 / float32 choices
- **Use Latest best.pt** button
- **Stop Export** button

## Install and run

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

## Notes

- Training/validation/export run through internal Python service wrappers (no external `yolo` shell dependency required).
- Device selection supports Auto/CUDA/CPU paths.
- Session scanning can repair older misplaced label paths into canonical YOLO layout.

See `custom_trainer/assets/pi_runtime/README_PI.md` for Pi-side TFLite runtime notes.
- Training / Validation / Export use Ultralytics through an internal Python runner module, so they do not depend on the external `yolo` shell command.
- Validation prediction runs now save into the session-oriented runs folder and the preview panel loads the boxed output automatically.
- Single-session folders such as `session/images/*.jpg` save labels to `session/labels/*.txt`.
- Older misplaced labels under `session/images/labels/*.txt` or `session/labels/images/*.txt` are auto-repaired into the canonical YOLO path when sessions are scanned.

- Screen-aware startup sizing keeps the main window inside the available desktop area on smaller displays.
