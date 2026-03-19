# PiServer

PiServer is a modular Flask-based runtime for PiCar control, recording, model inference, and browser-based operation.

## Why PiServer exists

Compared with older single-script flows, PiServer keeps a persistent backend running so you can:

- keep the UI available while the Pi is on,
- switch algorithms and runtime settings without rebooting,
- isolate camera/motor/recording/control concerns into separate services,
- and manage runtime behavior from one web workspace.

## Core capabilities

- Manual / Training / Auto / Camera workspace tabs.
- Dock-style draggable/resizable panels.
- Live MJPEG preview with camera backend status.
- Runtime algorithm switching and parameter tuning.
- TFLite model upload/list/load.
- Recording start/stop with structured session storage.
- Runtime config save/reload.
- Emergency stop.
- Camera settings panel with apply + camera restart action.
- Motor settings panel for direction, trim/bias, and safety-aware apply.

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

## Prerequisites

- Python 3.11 recommended.
- Raspberry Pi OS (for CSI camera and GPIO motor control).
- Browser on same local network for UI access.

Optional Pi-only runtime packages:

- `picamera2`
- `tflite-runtime`
- `RPi.GPIO`

If optional packages are unavailable, PiServer falls back:

- camera -> OpenCV webcam or generated placeholder frame,
- model inference -> disabled,
- motor output -> simulated console output.

## Quick start (Raspberry Pi)

```bash
cd ~/PiServer
python3 -m pip install -r requirements.txt --break-system-packages
python3 server.py
```

Open in browser:

```text
http://<pi-ip>:5000
```

## Quick start (development machine)

```bash
cd PiServer
python -m pip install -r requirements.txt
python server.py
```

Use this mode for UI/logic testing when Pi hardware is not attached.

## Runtime behavior model

PiServer keeps a background loop running continuously:

1. camera service fetches frames,
2. control loop runs at configured tick rate,
3. selected algorithm computes steering/throttle,
4. motor service applies clamped output,
5. recorder stores data if recording is enabled.

This design allows live mode switching, parameter updates, and continuous UI operation.

## Recording format

Each run is saved under:

```text
data/records/<session>/
```

`records.jsonl` rows include:

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

Image filenames are timestamp-based to maintain natural ordering and reduce collisions.

## Configuration files

- Runtime defaults: `config/runtime.json`
- System service template: `boot/pi_server.service`

When editing runtime config, keep units and expected ranges explicit in PR notes.

## Auto-start on boot (systemd)

```bash
sudo cp boot/pi_server.service /etc/systemd/system/pi_server.service
sudo systemctl daemon-reload
sudo systemctl enable pi_server.service
sudo systemctl start pi_server.service
sudo systemctl status pi_server.service
```

If installed in a non-default location, update `WorkingDirectory` and `ExecStart` in the service file.

## Updating code

Web update/restart controls were removed in version `0_1_14`. Use terminal-based updates:

```bash
cd /home/pi/PiDrive
git pull --ff-only
cd PiServer
python3 server.py
```

If managed by systemd:

```bash
sudo systemctl restart pi_server.service
```

## Safety notes

- Emergency stop should always be tested after setup.
- Motor outputs are clamped by runtime limits, but incorrect calibration can still be unsafe.
- Keep the web UI on a trusted local network; do not expose directly to the public internet.

## Main extension points

- Algorithms: `piserver/algorithms/`
- Runtime wiring: `piserver/app.py`
- UI template: `piserver/web/templates/index.html`
- UI logic/styles: `piserver/web/static/app.js`, `piserver/web/static/styles.css`

## Recent highlights

### PiServer `0_2_1`

- Manual tab supports both forward and reverse drive from joystick.
- Keyboard driving supports `W/A/S/D` and arrow keys while focused.
- Motor tab exposes left/right direction, per-motor max speed, and bias trim.

### PiServer `0_2_8`

- Added dedicated `steering_direction` motor setting.
- Motor save/apply persists steering direction into `config/runtime.json`.
- Motor UI text clarifies saved steering direction behavior.
