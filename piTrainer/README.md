# piTrainer_0_2_0

A PySide6 desktop training app for PiCar datasets.

This version replaces the earlier Streamlit browser UI with a native desktop GUI built in **PySide6**.
It keeps the PiCar record format and splits the app into:

- **pages**: one script per page
- **panels**: one script per panel inside each page
- **services**: one script per sub-function / business logic task

## Main features

- Load PiCar recordings from `data/records/<session>/records.jsonl` and `images/`
- Select one or more sessions
- Preview records and sample images
- Inspect dataset stats
- Split train / validation sets by session to reduce leakage
- Train a small CNN for steering and throttle on PC
- Export `.keras` and `.tflite` models
- Optional INT8 TFLite export with representative data

## Folder structure

```text
piTrainer_0_2_0/
├── main.py
├── README.md
├── requirements.txt
├── run_windows.bat
├── run_linux_mac.sh
├── PATCH_NOTES/
│   └── PATCH_NOTES_piTrainer_0_2_0.md
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
.venv\Scriptsctivate
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
- Dataset stats panel
- Preview panel

Sub-functional scripts used by the page:
- session discovery
- JSONL record loading
- stats calculation
- preview row/image extraction

### Page 2: Train
Panels:
- Split summary panel
- Training config panel
- Training control panel
- Training history panel

Sub-functional scripts used by the page:
- session-based split
- TensorFlow dataset creation
- model build / compile
- background training worker

### Page 3: Export
Panels:
- Model status panel
- Export options panel
- Export actions panel

Sub-functional scripts used by the page:
- save `.keras`
- export `.tflite`
- representative dataset generation for INT8 export

## PiCar record format expected

The loader expects session folders like this:

```text
data/
└── records/
    └── my_session/
        ├── records.jsonl
        └── images/
```

The loader is tolerant to field name variations, including:

- steering: `steering`, `angle`, `user/angle`, `user_angle`, `target_steering`
- throttle: `throttle`, `user/throttle`, `user_throttle`, `target_throttle`
- image path: `image`, `img`, `filepath`, `file`, `filename`, `path`
- mode: `mode`, `drive_mode`

It also keeps optional metadata such as:

- `frame_id`
- `session`
- `mode`
- `cam_w`, `cam_h`
- `camera_w`, `camera_h`
- `format`

## Notes

- Training and export need TensorFlow.
- If TensorFlow is missing, the Data page still works, and the app will show a friendly message on Train / Export.
- The UI is desktop-native and does **not** require a browser.
