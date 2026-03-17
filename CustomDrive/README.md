# CustomDrive

CustomDrive is a mission-controller package for competition-style autonomous tasks.

It runs the same finite-state mission loop in two mirrored modes:

1. **No GUI (terminal-first)** for lowest overhead and quickest iteration.
2. **Web GUI (PiServer-style)** for live observability and operator control.

## Mission loop

1. navigate to search area
2. detect and align to target
3. approach + pickup
4. navigate to drop area
5. detect and align to drop zone
6. approach + release
7. repeat by configured cycle count

## Install

```bash
cd CustomDrive
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Shared runtime settings (GUI + no GUI)

Settings are saved in:

- `CustomDrive/config/runtime_settings.json`

These settings are loaded by **both**:

- `python run_custom_drive_web.py`
- `python run_custom_drive_demo.py`

You can edit settings from the GUI **Settings** panel and click **Save Settings**, or save from CLI:

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode live --save-settings \
  --cam-width 640 --cam-height 360 --cam-fps 30 \
  --left-max-speed 0.9 --right-max-speed 0.92
```

## Run no-GUI (best performance)

### Simulation mode (default)

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode sim --cycles 2
```

### Live mode (real camera + motor via PiServer services)

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode live --cycles 2
```

## Run Web GUI

### Simulation mode

```bash
cd CustomDrive
python run_custom_drive_web.py
```

Open `http://localhost:5050`.

### Live mode

```bash
cd CustomDrive
CUSTOMDRIVE_MODE=live python run_custom_drive_web.py
```

Open `http://localhost:5050` and verify:

- mission state and command telemetry updates
- video feed is live in the right panel
- Start/Stop/Step/Reset controls work
- Settings can be saved and reused in terminal mode

## Notes

- In `live` mode, perception uses camera frames and color-based object proposals for `he3` and `he3_zone` labels.
- If camera/GPIO dependencies are unavailable, runtime falls back to `sim` safely.
- Terminal and GUI entrypoints both run the same mission controller logic, so behaviour stays mirrored.
