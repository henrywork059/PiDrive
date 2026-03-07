# piTrainer_0_3_6

A PySide6 desktop training app for PiCar datasets.

This desktop app replaces the earlier Streamlit browser UI with a native **PySide6** interface and starts in **dark mode by default**.
It keeps the PiCar record format and is organised into:

- **pages**: one script per page
- **panels**: one script per panel inside each page
- **services**: one script per sub-function / business logic task

## Current main features

- Load PiCar recordings from `data/records/<session>/records.jsonl` and `images/`
- Select one or more sessions from a saved record-root folder
- Merge multiple sessions into a new session
- Filter loaded preview frames by text, mode, steering range, and speed range
- Preview records and images in separate panels
- Edit steering and speed directly from the preview area
- Overlay speed / steering / drive-arrow graphics on the frame preview
- Plot useful session statistics on the Data page
- Delete selected frames from both `records.jsonl` and the matching image file
- Preprocess the loaded dataset for training
- Balance overrepresented near-zero steering rows
- Synthesize extra training rows with:
  - left-right mirrored copies
  - color-shifted copies
- Split train / validation sets by session to reduce leakage
- Train a small CNN for steering and throttle on PC
- Validate a trained model on filtered / train / validation rows
- Export `.keras` and `.tflite` models
- Optional INT8 TFLite export with representative data

## Folder structure

```text
current_piTrainer_folder/
├── main.py
├── README.md
├── requirements.txt
├── run_windows.bat
├── run_linux_mac.sh
├── PATCH_NOTES/
│   ├── PATCH_NOTES_piTrainer_0_2_1.md
│   ├── ...
│   └── PATCH_NOTES_piTrainer_0_3_6.md
└── piTrainer/
    ├── app.py
    ├── app_state.py
    ├── main_window.py
    ├── pages/
    ├── panels/
    ├── services/
    ├── ui/
    └── utils/
```

## Recommended Python version

Use **Python 3.11** for the smoothest TensorFlow install experience.
Python 3.12 may also work depending on platform.

## Install

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## App pages

### Data
Panels include:
- Session Source
- Frame Filter
- Quick Actions
- Data Control
- Merge Sessions
- Record Preview
- Image Preview
- Overlay Controls
- Playback Control
- Data Plot

### Preprocess
Panels include:
- Source Summary
- Preprocess Config
- Preprocess Actions
- Preprocess Preview
- Preprocess Log

Preprocess can:
- keep only rows matching your filters
- reduce straight-driving bias by balancing near-zero steering rows
- resize training images logically for the Train tab
- add mirrored copies for steering data
- add deterministic color-variation copies
- update the active in-memory training dataset without modifying source files

### Train
Panels include:
- Split Summary
- Training Config
- Training Controls
- Training History
- Training Log

### Validation
Panels include:
- Validation Summary
- Validation Config
- Validation Actions
- Validation Plot

### Export
Panels include:
- Model Status
- Export Options
- Export Actions
- Export Log

## Notes

- The GUI launches in dark mode by default.
- Training, validation, and export need TensorFlow.
- The Data page supports dockable panels and layout reset.
- The Preprocess tab can create synthetic rows without overwriting original images or JSONL files.
