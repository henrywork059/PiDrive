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
