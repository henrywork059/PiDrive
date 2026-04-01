# PiServer

PiServer is the modular PiCar runtime backend/web UI for manual driving, recording, model management, camera operations, and control-loop orchestration.

## Quick start

```bash
cd PiServer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Open:

```text
http://<pi-ip>:5000
```

## Current snapshot code markers

- App version constant: `piserver/app.py`
- Layout/localStorage namespace keys: `piserver/web/static/app.js`

Always align release docs to these files (not patch-note filenames alone).

## Runtime architecture

- Flask web app + MJPEG streaming endpoints
- modular services (camera, motor, recording, algorithms, runtime state)
- dock-style web workspace with per-page panel layouts
- runtime config save/reload support

## Optional Pi-only dependencies

- `picamera2`
- `RPi.GPIO`
- `tflite-runtime`

If unavailable, PiServer may run with simulated/fallback behavior depending on service.

## Key files

- Entry point: `server.py`
- Runtime config: `config/runtime.json`
- Backend wiring: `piserver/app.py`
- Front-end UI: `piserver/web/templates/index.html`
- Front-end logic: `piserver/web/static/app.js`
- Front-end styles: `piserver/web/static/styles.css`

## Systemd auto-start (optional)

```bash
sudo cp boot/pi_server.service /etc/systemd/system/pi_server.service
sudo systemctl daemon-reload
sudo systemctl enable pi_server.service
sudo systemctl restart pi_server.service
```

Adjust `WorkingDirectory`/`ExecStart` in the service file to match your install path.

## Bug-prevention reference

For layout versioning and compact-UI regression prevention practices, see:
- `../BUG_PREVENTION_NOTES.md`
