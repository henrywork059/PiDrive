# PiServer

PiServer is a refactored web-control backend for the PiCar project.

## What this build changes

- Starts as one persistent backend service instead of one fixed script flow.
- Keeps the web UI available whenever the Pi is on.
- Lets you switch algorithms at runtime from the web page.
- Separates camera, motor, model, recording, and control loop logic into modules.
- Adds a dock-style web workspace with saved panel layouts in the browser.
- Adds runtime config save/reload.
- Removes the web update / restart workflow. Code updates are now meant to be done from the terminal with `git pull`.

## Folder layout

```text
PiServer/
  server.py
  requirements.txt
  README.md
  boot/pi_server.service
  config/runtime.json
  models/
  data/records/
  piserver/
    app.py
    core/
    algorithms/
    services/
    web/
```

## Quick start on Raspberry Pi

1. Put the folder on the Pi, for example in `~/PiServer`
2. Install dependencies
3. Start the server
4. Open the Pi IP address in your browser

```bash
cd ~/PiServer
python3 -m pip install -r requirements.txt --break-system-packages
python3 server.py
```

Then open:

```text
http://<pi-ip>:5000
```

## Optional Pi-only packages

These are optional and only needed if the hardware/software is available on the Pi:

- `picamera2`
- `tflite-runtime`
- `RPi.GPIO`

If they are missing, PiServer falls back safely:
- camera -> OpenCV webcam or generated placeholder frame
- model inference -> disabled
- motor output -> simulated console output

## Auto-start on boot

The file `boot/pi_server.service` is included.

Example install:

```bash
sudo cp boot/pi_server.service /etc/systemd/system/pi_server.service
sudo systemctl daemon-reload
sudo systemctl enable pi_server.service
sudo systemctl start pi_server.service
sudo systemctl status pi_server.service
```

Edit the `WorkingDirectory` and `ExecStart` paths inside the service file if your install path is different.

## Web features

- Manual / Training / Auto workspace tabs
- Draggable + resizable dock-style panels on larger screens
- Live MJPEG viewer
- Runtime algorithm switching
- Runtime parameter tuning
- TFLite model upload/list/load
- Recording toggle
- Runtime config save/reload
- Emergency stop

## Runtime behavior design

PiServer uses a background control loop:

- camera service runs continuously
- web server stays alive
- control service runs at fixed rate
- selected algorithm computes steering/throttle
- motor service applies output
- recorder stores data if recording is enabled

That means:
- manual changes can happen live
- selected algorithm can change live
- config values can change live

## Recording format

Each session is stored under `data/records/<session>/`

Each JSONL row stores:

- `frame_id`
- `session`
- `ts`
- `image`
- `steering`
- `throttle`
- `mode`
- `camera_width`
- `camera_height`
- `camera_format`

Image names are timestamp-based so they sort naturally and do not repeat between sessions.

## Safety notes

- Emergency stop overrides algorithm output.
- Motor output is always clamped by runtime limits.
- Keep this web UI on a trusted local network only.

## Main files to edit later

- algorithms: `piserver/algorithms/`
- runtime defaults: `config/runtime.json`
- web UI: `piserver/web/templates/index.html`, `piserver/web/static/app.js`, `piserver/web/static/styles.css`
- backend wiring: `piserver/app.py`

## Updating code from the terminal

Web update and restart controls were removed in `0_1_14`.

Use the terminal instead:

```bash
cd /home/pi/PiDrive
git pull --ff-only
cd PiServer
python3 server.py
```

If you run PiServer with `systemd`, restart it after pulling:

```bash
sudo systemctl restart pi_server.service
```
