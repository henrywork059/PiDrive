# piTrainer

## Model deployment manifests (0.11.3, U27)

Exporting a steering model as `.keras` or `.tflite`, or using the
**Save Trained Model** action, now writes an adjacent
`<model filename>.manifest.json` file. It records steering-control family,
the RGB/NHWC input geometry, [0,1] normalization, ordered
`[steering, throttle]` interpretation, quantization mode, training seed,
and a SHA-256 checksum of the exported model bytes. An export reports a
clear error if its manifest cannot be saved; it never claims that a
manifest-less new export was fully deployed.

Transfer **both files** to PiSD or PiServer, and keep them together when
renaming/copying the model. If you intentionally use an older sidecar-free
model, the runtime warns and performs available tensor-shape checks instead.
A manifest that is present but inconsistent, corrupted, from the wrong model
family, or bound to a different checksum is rejected.

This does not change the accepted training architecture, seed defaults,
non-overwriting model names, exports, data split, or validation workflow.
Run actual TensorFlow conversion and Pi hardware preflight on the target
machines before trusting a deployment.

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
