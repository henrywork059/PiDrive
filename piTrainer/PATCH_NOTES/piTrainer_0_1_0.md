# PATCH NOTES — piCar_trainer_app_0_1_0

Date: 2026-03-05

## Goal
Create a **new PC-side training app** written in Python with a GUI that is:
- Easy to run and user-friendly
- Modular: main script → pages → panels → functions

## What’s included
### Architecture (as requested)
- `picar_trainer_app/main.py` is the **single entry script** and router.
- Each **page** has its own script in `picar_trainer_app/pages/`:
  - `data.py`, `train.py`, `export.py`
- Each **panel** is its own script in `picar_trainer_app/panels/`:
  - Data panels: session selector, preview table, image preview
  - Train panels: hyperparams view, train controls, metrics plots
  - Export panels: save/export controls
- Each **function area** is separated in `picar_trainer_app/core/`:
  - `data_io.py`, `dataset.py`, `model.py`, `exporter.py`, `utils.py`

## Data format assumptions
- `data/records/<session>/records.jsonl`
- `data/records/<session>/images/`
- Each JSONL line should include at least:
  - image path (key tolerant: `image`, `filename`, `path`, …)
  - steering (key tolerant: `steering`, `angle`, …)
  - throttle (key tolerant: `throttle`, …)
- Optional fields kept if present (e.g., `frame_id`, `mode`, camera info)

## Verification steps
1. Copy a PiCar `data/records/` folder onto your PC.
2. Run:
   - `pip install -r requirements.txt`
   - `streamlit run picar_trainer_app/main.py`
3. Go to **Data** page → select sessions → confirm images preview.
4. Go to **Train** page → click Start training → confirm curves appear.
5. Go to **Export** page → save `.keras` and export `.tflite`.

## Future improvements (not implemented yet)
- Label normalization + deadzone shaping
- Better augmentation (crop/shift) with steering-aware correction
- Advanced models (MobileNetV3, NVIDIA-style) + model manager
- Full INT8 quantization with optional int8 IO for faster Pi inference
