# PiSD AI Runtime Setup

PiSD can list uploaded `.tflite` model files without an AI runtime, but it cannot run them until the same Python environment that starts PiSD can import a TFLite interpreter.

## Symptom

AI Mode shows:

```text
Runtime: TFLite missing / Keras missing
Backend: load_failed
Failed to load AI model: TFLite runtime is not installed...
```

This means the model file is present, but the Pi is missing the inference package.

## Recommended install on Raspberry Pi

From the PiSD folder on that Pi:

```bash
cd ~/PiDrive/PiSD
python3 scripts/install_ai_runtime.py --runtime tflite-runtime
python3 scripts/check_ai_runtime.py
```

Then restart PiSD and click **Load model** again in AI Mode.

## Fallback install

If `tflite-runtime` is not available for that Pi/Python combination, try the newer LiteRT package:

```bash
cd ~/PiDrive/PiSD
python3 scripts/install_ai_runtime.py --runtime ai-edge-litert
python3 scripts/check_ai_runtime.py
```

## Important environment rule

Install the runtime with the same `python3` command/environment that runs PiSD. If PiSD is run by a systemd service, restart the service after installation.

Example service restart:

```bash
sudo systemctl restart pisd.service
sudo systemctl status pisd.service
```

## Validation

A working `.tflite` runtime check should report:

```text
OK: PiSD can load .tflite models with this Python environment.
```

If the check script still reports missing imports, the model will continue to show `load_failed` until a runtime is installed.
