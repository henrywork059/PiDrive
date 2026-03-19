# Pi Runtime Bundle

This bundle is intended for running **TFLite object detection inference on Raspberry Pi** after training/exporting models on a desktop machine.

## What this bundle provides

- Pi-focused inference runner for images/camera input.
- Lightweight benchmark script for measuring model latency.
- Compatibility with either `tflite-runtime` or TensorFlow Lite interpreter.

## Recommended deployment flow

1. Train and export model on desktop (`CustomTrainer`).
2. Copy `model.tflite` and `labels.txt` to Pi.
3. Install Pi runtime dependencies.
4. Run detection script against image/camera.
5. Benchmark and tune model/input size for target FPS.

## Install on Raspberry Pi

Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements_pi.txt
```

## Interpreter requirement

You need exactly one TFLite interpreter source:

- `tflite-runtime` (preferred lightweight option on Pi), or
- `tensorflow` (uses `tensorflow.lite.Interpreter`).

## Run on a single image

```bash
python run_tflite_detect.py --model model.tflite --labels labels.txt --source test.jpg
```

## Run on Pi/USB camera

```bash
python run_tflite_detect.py --model model.tflite --labels labels.txt --source 0
```

## Benchmark model

```bash
python benchmark_tflite.py --model model.tflite
```

## Practical performance guidance

- Start with smaller input sizes (for example, 320 or 416).
- Prefer compact architectures for stable Pi performance.
- INT8 export is often the best first format to evaluate on Pi.
- Validate accuracy/performance tradeoff on the real deployment camera.

## Troubleshooting

- If interpreter import fails, verify only one interpreter path is installed and active in the venv.
- If camera source fails, confirm camera index/device permissions and Pi camera stack setup.
- If FPS is too low, reduce input size and confirm CPU governor/thermal limits.
