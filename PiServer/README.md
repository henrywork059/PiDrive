# PiServer

PiServer is a refactored web-control backend for the PiCar project.

## What this build changes

- Starts as one persistent backend service instead of one fixed script flow.
- Keeps the web UI available whenever the Pi is on.
- Lets you switch algorithms at runtime from the web page.
- Separates camera, motor, model, recording, control loop, and update logic into modules.
- Adds a dock-style web workspace with saved panel layouts in the browser.
- Adds runtime config save/reload.
- Adds safe Git pull / service restart actions from the web UI.

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
2. Create a virtual environment
3. Install dependencies
4. Start the server
5. Open the Pi IP address in your browser

```bash
cd ~/PiServer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
- Git status / pull
- Service restart
- Emergency stop

## Runtime behavior design

PiServer now uses a background control loop:

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
- larger code changes can be pulled from Git and restarted safely

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

- Git update and service restart actions are blocked unless the vehicle is stopped.
- Emergency stop overrides algorithm output.
- Motor output is always clamped by runtime limits.
- Keep this web UI on a trusted local network only.

## Main files to edit later

- algorithms: `piserver/algorithms/`
- runtime defaults: `config/runtime.json`
- web UI: `piserver/web/templates/index.html`, `piserver/web/static/app.js`, `piserver/web/static/styles.css`
- backend wiring: `piserver/app.py`


## Repo-backed update setup (0_1_11)

To use **Update from Repo**, run PiServer from a real Git checkout, not from a plain copied folder.
A simple setup on the Pi is:

```bash
cd /home/pi
git clone --filter=blob:none --sparse https://github.com/henrywork059/PiDrive.git
cd PiDrive
git sparse-checkout set PiServer
cd PiServer
python3 -m pip install -r requirements.txt --break-system-packages
python3 server.py
```

The included `boot/pi_server.service` now points to `/home/pi/PiDrive/PiServer` and uses `/usr/bin/python3` so it works without a virtual environment.

When PiServer is running from that repo-backed folder, the web UI can:
- check the active repo, branch, commit, and remote
- run `git pull --ff-only` from the parent `PiDrive` repo
- restart the service after an update

Update is blocked when:
- recording is on
- throttle is not zero
- E-stop is not engaged
- Git has local modified files


## Restart from web (0_1_12)

`Restart Server` now re-launches the current PiServer process directly, so it works both when you start PiServer with `python3 server.py` and when you run it from a `systemd` service.

Typical flow after an update:

1. Click `Update from Repo`
2. Read the update result in the System panel
3. Click `Restart Server`
4. Wait a few seconds for the page to reconnect

The update result now shows whether the Git commit changed. If a new commit was pulled, the message tells you to restart so the new code is loaded.
