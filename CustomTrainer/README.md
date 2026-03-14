# CustomTrainer

CustomTrainer is a draft desktop trainer app for **object detection** workflows.
It is designed as a modular PC-side tool with separate pages for:

- Dataset setup and scanning
- Basic YOLO annotation editing
- Training launch and log viewing
- Validation / prediction launch
- Pi-oriented export launch
- Pi deployment bundle creation

This scaffold is now biased toward a **PC-train / Raspberry Pi-run** workflow for your competition robot.

## Main features

- Desktop GUI built with `tkinter` and `ttk`
- Separate pages/scripts for each workflow area
- Scans YOLO-style datasets
- Creates `dataset.yaml`
- Basic rectangle annotation editor for YOLO labels
- Launches Ultralytics YOLO train / val / predict / export jobs
- Pi-friendly TFLite export defaults
- Pi deployment bundle builder with runtime scripts
- Built-in log panel

## Suggested dataset structure

```text
my_dataset/
  images/
    train/
    val/
  labels/
    train/
    val/
  dataset.yaml
  classes.txt
```

## Install on PC

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python run_custom_trainer.py
```

## Recommended Pi workflow

1. Train a **small model** first, such as a YOLO nano variant.
2. Keep the input size modest, usually **320** or **416**.
3. Export to **TFLite** from the Export page.
4. Prefer **INT8** first for Pi, with `dataset.yaml` provided for calibration.
5. If INT8 export/runtime has issues, try **float16**.
6. Use the **Pi Deploy** page to build a ready-to-copy runtime bundle.
7. Copy the generated `pi_bundle/` folder to the Raspberry Pi.
8. On the Pi, install the bundle requirements and run `run_tflite_detect.py`.

## Important note

This app now prepares the model for Raspberry Pi deployment, but actual Pi compatibility still depends on:

- the Raspberry Pi model and OS
- whether `tflite-runtime` or `tensorflow` is installed on the Pi
- whether the exported model uses ops supported by that runtime
- how large the model/input size is for your target FPS

So this update makes the training/export path **Pi-oriented and deployable**, but you should still test the exported `.tflite` on the real Pi early.

## Included Pi bundle files

The Pi Deploy page generates a `pi_bundle/` folder containing:

- exported `.tflite` model
- `labels.txt`
- `model_config.json`
- `run_tflite_detect.py`
- `benchmark_tflite.py`
- `requirements_pi.txt`
- `README_PI.md`

## Recommended next improvements

- Add training presets for your exact competition classes
- Add direct export-to-PiServer handoff
- Add live camera validation from USB webcam / RTSP stream
- Add confidence-matrix viewer and per-class metrics charts
- Add model packaging for your PiCar autopilot/object-pick pipeline
