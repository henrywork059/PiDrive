# piTrainer

`piTrainer` is a PySide6 desktop app for PiCar steering/throttle workflows: dataset curation, preprocessing, model training, validation, and export.

## What you can do in piTrainer

- Load recorded sessions (`records.jsonl` + image folders).
- Inspect and edit frame metadata.
- Filter and rebalance steering distributions.
- Build processed datasets for training.
- Train steering/throttle models.
- Review validation metrics and prediction behavior.
- Export models as `.keras` and `.tflite`.

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

## Prerequisites

- Python **3.11** recommended.
- Desktop environment (Windows/macOS/Linux with GUI support).
- TensorFlow-compatible environment for train/validation/export pages.

## Install

From `piTrainer/`:

```bash
python -m venv .venv
```

Activate the environment:

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

Helper launchers are also provided:

- Windows: `run_windows.bat`
- macOS/Linux: `run_linux_mac.sh`

## Page-by-page guide

### Data page

Use this page to load and inspect raw sessions before training.

- choose source sessions,
- filter rows by conditions,
- preview images and metadata,
- perform merge/delete operations,
- inspect quick plots before preprocessing.

### Preprocess page

Use this page to create model-ready datasets.

- resize and normalize images,
- rebalance near-zero steering dominance,
- optionally augment rows (mirror/color options),
- generate a consistent processed dataset split.

### Train page

Use this page to configure and run training jobs.

- review split summary,
- set training parameters,
- start/monitor training,
- inspect history and per-epoch signals.

### Validation page

Use this page to evaluate trained models.

- run validation passes,
- inspect plots/metrics,
- review frame-level predictions.

### Export page

Use this page for deployment artifacts.

- choose export format,
- verify current model status,
- export `.keras` or `.tflite` outputs,
- review export log for warnings.

## Suggested workflow

1. Load sessions in **Data**.
2. Clean/filter rows.
3. Build balanced dataset in **Preprocess**.
4. Train model in **Train**.
5. Evaluate in **Validation**.
6. Export artifact in **Export**.
7. Deploy to Pi runtime for road testing.

## Notes and troubleshooting

- UI starts in dark mode.
- Keep source sessions immutable when possible; write outputs to dedicated processed folders.
- If training tabs fail to load, verify TensorFlow package compatibility with your Python version.
- For large datasets, prefer SSD storage and avoid network-mounted folders.
