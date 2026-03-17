# CustomTrainer

CustomTrainer is a PySide6 desktop YOLO workflow with session-based annotation and model lifecycle pages.

## Main tabs

- **Marking**: browse sessions, draw/edit bounding boxes, maintain `classes.txt`, save YOLO labels.
- **Train**: run Ultralytics training jobs with device selection.
- **Validate**: run validation/prediction and review results.
- **Export**: export trained weights (TFLite/ONNX/OpenVINO/TorchScript).
- **Pi Deploy**: deploy-focused utilities for Raspberry Pi runtime artifacts.

## Layout

```text
CustomTrainer/
├── run_custom_trainer.py
├── requirements.txt
├── custom_trainer/
│   ├── app.py
│   ├── state.py
│   ├── services/
│   ├── ui/
│   ├── utils/
│   └── assets/pi_runtime/
└── PATCH_NOTES/
```

## Install and run

```bash
cd CustomTrainer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_custom_trainer.py
```

## Notes

- Training/validation/export run through internal Python service wrappers (no external `yolo` shell dependency required).
- Device selection supports Auto/CUDA/CPU paths.
- Session scanning can repair older misplaced label paths into canonical YOLO layout.

See `custom_trainer/assets/pi_runtime/README_PI.md` for Pi-side TFLite runtime notes.
