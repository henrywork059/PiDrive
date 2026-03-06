# piTrainer_0_2_4

A PySide6 desktop training app for PiCar datasets.

This version replaces the earlier Streamlit browser UI with a native desktop GUI built in **PySide6** and starts in **dark mode by default**.
It keeps the PiCar record format and splits the app into:

- **pages**: one script per page
- **panels**: one script per panel inside each page
- **services**: one script per sub-function / business logic task

## Main features

- Load PiCar recordings from `data/records/<session>/records.jsonl` and `images/`
- Select one or more sessions
- Filter loaded preview frames by text and mode
- Preview records and sample images
- Auto-play the preview frames
- Delete the selected frame from both `records.jsonl` and the matching image file
- Inspect dataset stats
- Split train / validation sets by session to reduce leakage
- Train a small CNN for steering and throttle on PC
- Export `.keras` and `.tflite` models
- Optional INT8 TFLite export with representative data

## Folder structure

```text
piTrainer_0_2_4/
├── main.py
├── README.md
├── requirements.txt
├── run_windows.bat
├── run_linux_mac.sh
├── PATCH_NOTES/
│   └── PATCH_NOTES_piTrainer_0_2_4.md
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

## How the app is organised

### Page 1: Data
Panels:
- Root path panel
- Session list panel
- Frame filter panel
- Data control panel
- Dataset stats panel
- Record preview panel
- Image preview panel

Sub-functional scripts used by the page:
- session discovery
- JSONL record loading
- stats calculation
- preview row/image extraction
- preview filtering
- record deletion

### Page 2: Train
Panels:
- Split summary panel
- Training config panel
- Training control panel
- Training history panel

### Page 3: Export
Panels:
- Model status panel
- Export options panel
- Export actions panel

## Notes

- The GUI launches in dark mode by default.
- Training and export need TensorFlow.
- The Data page has a **Show Shortcuts** button, an **Auto Play Frames** button, and a **Delete Selected Frame** button.
- Press `Space` to start or stop frame autoplay.
- The session list checkbox color has been brightened for dark mode visibility.
