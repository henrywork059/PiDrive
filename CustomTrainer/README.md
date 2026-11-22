# CustomTrainer

CustomTrainer is a PySide6 desktop workflow for object-detection data labeling, training, validation, export, and exported-model validation.

## Launch

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

## Current snapshot version marker

Window title/version is set in:
- `custom_trainer/ui/main_window.py`

Use that file as source of truth for documentation version text.

## Tabs and responsibilities

- **Marking**: session discovery, annotation, class management, quick deploy labeling support
- **Training**: run training jobs and inspect logs/plots
- **Validation**: run validation/prediction for trained models
- **Export**: export trained weights (TFLite/ONNX/OpenVINO/TorchScript)
- **Export Validate**: run inference/validation on exported models

## Dataset integrity and YOLO annotation validation (0_2_12)

The generated `dataset.yaml` uses session-aware train/validation partitions.
Whole capture sessions stay in one partition, including sessions connected
by identical image bytes. The approximate 10% validation target is secondary
to keeping independent capture sessions separate.

**At least two independent, non-duplicate sessions are required** for an
automatic validation holdout. If only one independent session exists, the
generated `val.txt` stays empty and Train, Validate and Export Validate
show a clear warning rather than reusing training images as validation.
You can label a second recording session and regenerate the dataset.

Before launching training or validation, the Run Log reports per-session
image counts, valid annotation counts, missing/empty labels, invalid box
counts and representative line-specific errors. The generated training
cache excludes invalid YOLO boxes (non-finite/out-of-range coordinates,
boxes extending beyond image bounds, invalid class IDs and zero-size
boxes). Source labels are **not rewritten**; fix problematic labels in
Marking and prepare the dataset again.

Session-grouped splitting reduces leakage but cannot detect visually
near-identical frames with different bytes. Capture in distinct runs,
conditions or locations for stronger validation. The existing Marking
quick-deploy and Export Validate interfaces are unchanged.

## Immutable YOLO dataset cache generations (0_2_13, U25)

Training, Validation, and Export Validate now run against **private, immutable
dataset snapshots** in `.customtrainer_yolo_cache/generations/gen_*/`.
Preparing another dataset no longer deletes files referenced by an active
training process. Each run receives its own generation-local `dataset.yaml`,
`train.txt`, `val.txt`, copied image files, and validated training labels.

Dataset preparation first builds in a private `.building/` directory, checks
the complete image lists and label counts, writes a `cache_manifest.json`,
then atomically promotes the generation. Only after successful publication
does the familiar root `dataset.yaml` pointer change (via atomic file
replacement). If a build fails, the previous public YAML and old generations
remain intact. The Marking, training split, labeling, and exported-model
workflows are otherwise unchanged. Original images are **copied**, not
hard-linked: an in-place source image edit cannot alter a running snapshot.

**Retention:** There is **no automatic deletion** of prior generations or
the old pre-U25 cache layout. This uses additional disk space; check free space
when preparing large image datasets. Inspect caches from the CustomTrainer
project directory:

```bash
python manage_dataset_cache.py /path/to/sessions_root
```

After confirming training, validation, and external YOLO readers are finished,
explicitly prune old known generations:

```bash
python manage_dataset_cache.py /path/to/sessions_root --prune --confirm-idle
```

Pruning preserves at least the two newest generations, the currently selected
dataset YAML, generations younger than 24 hours, and any generation protected
by an active CustomTrainer Ultralytics subprocess lease. Other directories or
unknown cache formats are never removed. Do **not** manually delete or edit an
active `gen_*` directory. Jobs launched outside CustomTrainer may not hold
its reader lock: the `--confirm-idle` acknowledgement is therefore
important even when the CLI shows no busy generation.

The root `dataset.yaml` remains for backwards compatibility, but it points
to the latest published snapshot and can change on a later preparation.
For reproducible manual `yolo` commands, use the **generation-local
`dataset.yaml`** shown in the Run Log. Cache cleanup and Windows file-lock
handover should be verified on the target workstation before widespread use.

## Requirements and environment

- Python **3.11** recommended
- Install from `requirements.txt`
- GPU acceleration depends on local torch/cuda environment

## Operational notes

- UI state (splitters, last path) is persisted locally.
- If layout is abnormal after upgrades, reset state or ensure width clamping logic is active in Marking page.
- For Pi deployment helpers, see `custom_trainer/assets/pi_runtime/README_PI.md`.

## Bug-prevention reference

For recurring UI and deployment pitfalls derived from historical patch notes, see:
- `../BUG_PREVENTION_NOTES.md`
