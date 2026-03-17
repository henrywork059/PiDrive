# piTrainer

`piTrainer` is a PySide6 desktop application for PiCar steering/throttle workflows:

- load recorded sessions (`records.jsonl` + images)
- inspect/filter/edit frame metadata
- preprocess and rebalance datasets
- train steering/throttle models
- validate and review predictions
- export `.keras` and `.tflite` models

## Project layout

```text
piTrainer/
├── main.py
├── requirements.txt
├── README.md
├── run_windows.bat
├── run_linux_mac.sh
├── PATCH_NOTES/
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

## Install

Recommended Python: **3.11**.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Pages and capabilities

- **Data**: session source, frame filters, preview/edit panels, overlay/playback, merge/delete tools, plots.
- **Preprocess**: filtered dataset creation, balancing near-zero steering, image resize strategy, mirrored/color-augmented rows.
- **Train**: split summary, training config, training controls, history/epoch review.
- **Validation**: validation config/actions, metrics plots, frame review.
- **Export**: model status + export options/actions/log.

## Notes

- UI starts in dark mode.
- Data operations are designed to keep source/session organization explicit.
- Training/validation/export require TensorFlow-compatible dependencies.
