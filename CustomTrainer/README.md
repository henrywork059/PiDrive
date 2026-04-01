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
