# PiServer

PiServer is the web-control backend for the PiCar project.

## What this cumulative build includes

This `0_1_6` package includes the requested features from **0_1_1 through 0_1_6**:

- top drive-mode tabs for **Manual**, **Lane Detection**, and **Full Auto**
- mode-specific settings that change with the selected drive mode
- a dedicated **Calibration** tab for motor trim, overall speed cap, and turning ratio
- a dedicated **Camera** tab for stream, exposure, white balance, and image tuning
- runtime save/reload of all mode, calibration, and camera settings
- dock-style web workspace with saved layout per page
- demand-driven camera / lighter background load for Raspberry Pi
- Git status / **Update from Git** / service restart from the web UI

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

## Run it on the Pi without venv

If your PiServer folder is at `~/PiDrive/PiServer`:

```bash
cd ~/PiDrive/PiServer
python3 -m pip install -r requirements.txt --break-system-packages
python3 server.py
```

Then open:

```text
http://<pi-ip>:5000
```

Find the Pi IP with:

```bash
hostname -I
```

## Git-backed install for the web update button

The **Update from Git** button only works when PiServer is running from a real Git checkout.
A plain unzip at `/home/pi/PiServer` is not enough for `git pull`.

Recommended setup:

```bash
cd /home/pi
git clone --filter=blob:none --sparse https://github.com/henrywork059/PiDrive.git
cd PiDrive
git sparse-checkout set PiServer
cd PiServer
python3 -m pip install -r requirements.txt --break-system-packages
python3 server.py
```

That gives this runtime path:

```text
/home/pi/PiDrive/PiServer
```

## Auto-start on boot

This service file is set for the Git-backed layout above.

```bash
sudo cp boot/pi_server.service /etc/systemd/system/pi_server.service
sudo systemctl daemon-reload
sudo systemctl enable pi_server.service
sudo systemctl start pi_server.service
sudo systemctl status pi_server.service
```

Useful logs:

```bash
journalctl -u pi_server.service -n 100 --no-pager
```

## Web tabs

### Drive mode tabs

- **Manual**
- **Lane Detection**
- **Full Auto**

### Calibration tab

- left motor trim
- right motor trim
- global max speed
- turning ratio

### Camera tab

- resolution
- FPS
- format
- auto exposure on/off
- locked exposure time
- analogue gain
- exposure compensation
- auto white balance on/off
- brightness
- contrast
- saturation
- sharpness

All of these save into `config/runtime.json` when you use **Save Config**.

## Git / restart safety

Update and restart actions are blocked unless:

- recording is off
- throttle is zero
- emergency stop is enabled

This helps stop accidental updates while the car is moving.

## Notes on camera tuning

- Keep **Auto Exposure** on while first testing framing.
- Turn it off only when you want a more stable locked exposure during driving.
- Resolution / FPS / format changes reopen the camera backend.
- Exposure and image tuning values are applied live when possible.

## Main files to edit later

- algorithms: `piserver/algorithms/`
- runtime defaults: `config/runtime.json`
- web UI: `piserver/web/templates/index.html`, `piserver/web/static/app.js`, `piserver/web/static/styles.css`
- backend wiring: `piserver/app.py`
- Git update behavior: `piserver/services/update_service.py`


## 0_1_7 UI compatibility notes
- Mode tabs now switch locally first, then sync to the backend.
- Static JS/CSS now use a version query so browsers reload the new files after an update.
- Panel dragging/resizing is intended for desktop and tablet widths above about 700px. Drag panels by the panel header.
