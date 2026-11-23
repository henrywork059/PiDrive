# piTrainer

## Preview performance and memory (0.11.5, R38)

Image Preview now coalesces rapid row-navigation requests on the next Qt
event-loop turn. When you change frames, the old image clears **before** the
new frame's steering/speed labels appear; any superseded pending decode or
resize render is cancelled. The existing 450 ms **metadata edit** debounce is
not changed. This work does not move QPixmap/QPainter into a worker thread.

The shared scaled-pixmap cache retains only unannotated image previews, with
both its previous **96-item** cap and a new **64 MiB estimated decoded-pixel**
budget. Cached entries include source filename, requested display size,
horizontal-flip state, file modification time and file size. Replacing a
source file at the same path therefore invalidates its stale cached preview.
Overlay rendering still uses fresh copies and the existing PiSD road-guide
geometry; horizontally flipped frames still use the original flip transform.
The 64 MiB budget is **not** a cap on total process RSS or Qt/GPU allocations.

Baseline performance was measured using the exact byte-identical
`record_loader_service.py` from the 0.11.4 branch on Linux/Python 3.13,
with generated 426×240 JPEG files: **250 frames** loaded in 15.69 ms
(peak process RSS 96.02 MiB), **2,500** in 107.85 ms (98.39 MiB), and
**10,000** in 501.21 ms (112.22 MiB). These are one-run controlled
synthetic-session observations, **not** predictions of Windows or Pi
performance. The loader's image-path resolution and dataframe schema were
not changed by R38.

Reproduce the loader/peak-RSS benchmark on the target workstation:

```bash
cd piTrainer
python tests/benchmark_preview_r38.py --counts 250 2500 10000
python tests/benchmark_preview_r38.py --counts 250 2500 10000 --qt-preview
python -m unittest discover -s tests -p 'test_preview_r38.py' -v
```

The optional `--qt-preview` run uses an offscreen PySide6 application and
actual scaled pixmaps; it is necessary to measure native Qt preview costs.
Tests based on mock pixmaps validate the cache and cancellation policy but
do not replace real Windows image, overlay and flip verification.

## Data selection scope (0.11.4, R37)

The **Records** review table now shows a compact read-only scope strip:
**Visible**, **Selected visible**, **All active**, **Hidden**, and
**Generated**. Visible frames are filtered source rows currently in the
Records table. Selected visible means the actual selected table rows, even
after sorting. All active means all non-hidden frames loaded from the
currently loaded sessions (including generated variants and frames excluded
by the preview filter). Hidden counts distinct frames marked hidden in the
loaded sessions' JSONL metadata. Generated is the number of active
synthetic derivatives; they are normally excluded from editable Data review.
If hidden metadata cannot be read, the strip shows **Unavailable**, not 0.

**Bulk Edit, Hide Selected, and Apply AI Output** operate on selected visible
rows, **not all active frames**. Their confirmation messages say how many
selected visible rows are targeted and explicitly disclose whether generated
derivatives are present. Multi-frame Hide Selected requires an additional
confirmation; existing Confirm Hide and Confirm Overwrite safety checkboxes
remain mandatory. **Select Visible** selects just the currently filtered
preview rows. Sort order, source-row identities, Validation → Edit in Data →
Return navigation, and the read-only QAbstractTableModel are unchanged.

Hidden metadata is counted when the sessions are loaded or reloaded after
recovery; it is not re-scanned on every selection change. If an external
program changes JSONL files during a session, reload the sessions to refresh
the hidden total before performing a bulk operation.

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
