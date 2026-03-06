# PiCar Trainer App (PC)

This is a **Python training app that runs on your PC** (Windows/macOS/Linux).
It provides a user-friendly GUI (Streamlit) to:
- Load PiCar recordings from `data/records/<session>/records.jsonl` + `images/`
- Preview/inspect basic stats
- Train a small CNN to predict **steering + throttle**
- Export `.keras` and `.tflite` for deployment to the PiCar

## Folder structure
- `picar_trainer_app/main.py` : entry point (router + sidebar)
- `picar_trainer_app/pages/`  : pages (Data / Train / Export), one script each
- `picar_trainer_app/panels/` : panels, one script per panel
- `picar_trainer_app/core/`   : functional modules (data/dataset/model/export/utils)

## Install & run (PC)
```bash
cd piCar_trainer_app_0_1_0
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# run the GUI
streamlit run picar_trainer_app/main.py
```

## Notes
- Train on PC, then copy the exported `.tflite` to the PiCar.
- The loader is tolerant to field names:
  - steering: `steering` / `angle` / ...
  - throttle: `throttle` / ...
  - image path: `image` / `filename` / `path` / ...
