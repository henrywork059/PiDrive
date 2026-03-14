# CustomTrainer 0_1_2

CustomTrainer is now focused on a **single PySide6 marking workflow** that behaves much closer to **piTrainer**:

- load a sessions root folder
- automatically scan and list all sessions inside that folder
- browse images inside a selected session
- label images in one main marking tab
- save YOLO `.txt` labels beside the session structure

## What changed in 0_1_2

This patch intentionally simplifies the app.

- removed the multi-page trainer/export shell from the 0_1_1 UI flow
- kept the **PySide6 desktop style** and dark blue panel language similar to piTrainer
- changed the main workflow to a **single Marking tab**
- added **session-root scanning** so the app loads all sessions in a chosen folder
- added a **session list** and **image list** similar to piTrainer's data-loading workflow
- added a built-in **YOLO image labeler** with:
  - draw box by left-drag
  - select box by right-click
  - move selected box with arrow keys
  - delete selected box
  - change selected box class
  - save labels to YOLO text files
- added class loading from `classes.txt`, `dataset.yaml`, or `data.yaml`
- added class editing and saving back to `classes.txt`
- kept the docked log console and status bar for desktop workflow feedback

## Supported session layouts

CustomTrainer will scan the chosen folder and treat these as sessions when images are found:

### Layout A

```text
sessions_root/
  session_001/
    images/
    labels/
```

### Layout B

```text
sessions_root/
  session_001/
    frame_0001.jpg
    frame_0002.jpg
    labels/
```

### Layout C

```text
session_folder/
  images/
  labels/
```

If no label file exists yet, CustomTrainer will create one when you save.

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

## Shortcuts

- `Ctrl+S` save current labels
- `PageUp / PageDown` previous / next image
- `Delete` delete selected box
- `Arrow keys` move selected box
- `Shift + Arrow keys` move selected box faster
- `F1` show shortcuts

## Notes

- this patch is focused on **marking / labeling only**
- it is designed to feel closer to piTrainer's session-loading desktop workflow
- labels are saved in YOLO format as `.txt`
