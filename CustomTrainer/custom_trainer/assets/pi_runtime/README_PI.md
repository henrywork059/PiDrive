# Pi Runtime Bundle

This bundle is meant to run a **TFLite object detection model on Raspberry Pi**.

## Install on Pi

Create a venv if you want, then install:

```bash
pip install -r requirements_pi.txt
```

You need **one** TFLite interpreter source:
- `tflite-runtime`, or
- `tensorflow` (uses `tensorflow.lite.Interpreter`)

## Run on an image

```bash
python run_tflite_detect.py --model model.tflite --labels labels.txt --source test.jpg
```

## Run on the Pi camera / USB camera

```bash
python run_tflite_detect.py --model model.tflite --labels labels.txt --source 0
```

## Benchmark

```bash
python benchmark_tflite.py --model model.tflite
```

## Notes

- This runtime is optimized for a **Pi deployment path** where training is done on PC and inference is done on Pi.
- Prefer a small model and moderate image size such as 320 or 416 for better Pi performance.
- If INT8 export works for your model and dataset, it is usually the best first format to try on Pi.
