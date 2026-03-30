# PATCH NOTES — PiServer_0_4_8

## Baseline
- Stable baseline: `PiServer_0_4_0`
- Previous active patch: `0_4_7`
- This patch is built forward on top of the accepted `0_4_5` to `0_4_7` snapshot fixes and keeps those changes intact.
- No recent `0_4_x` UI/style/status fixes were removed.

## Request summary
The next reported bug is camera colour/tint: the live image looks red-tinted.

Requested work:
1. check the current camera-settings path for obvious bugs
2. add testing / diagnostic code to help verify camera settings on the Pi
3. package the result as a PiServer patch zip

## Problems found
### 1) Auto white balance UI wiring bug
The active PiServer web UI was posting camera settings using the field:
- `awb`

But `CameraService.apply_settings()` only read:
- `auto_white_balance`

That meant the AWB checkbox on the active page could appear to change, while the backend camera service kept using its previous AWB state.

This does **not** prove that AWB is the only cause of the red tint, but it is a real bug directly related to colour handling.

### 2) No dedicated PiServer camera tint diagnostic tool
PiServer had runtime camera controls, but no focused test utility to:
- capture a small comparison set of images under different colour-related settings
- record the effective PiServer camera config used for each capture
- dump backend diagnostics/metadata into one folder for review

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/tools/__init__.py`
- `PiServer/piserver/tools/camera_diagnostic.py`
- `PiServer/run_camera_settings_diagnostic.py`
- `PiServer/tests/test_camera_service.py`
- `PiServer/tests/test_camera_diagnostic.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_8.md`

## Exact changes made
### 1) Fixed AWB field compatibility
Updated PiServer so camera settings now accept both:
- `auto_white_balance`
- legacy/incorrect `awb`

Also updated the active frontend JS to send and read the correct `auto_white_balance` key.

Result:
- the camera AWB checkbox now actually reaches the backend
- older cached frontend payloads using `awb` still remain compatible

### 2) Added camera tint/settings diagnostic tool
Added a new standalone entry point:
- `PiServer/run_camera_settings_diagnostic.py`

It uses PiServer’s own `CameraService` and saves results under:
- `PiServer/data/camera_diagnostics/<timestamp>/`

The tool captures a comparison set aimed at red/cast issues:
- `baseline_runtime`
- `force_awb_on`
- `force_awb_off`
- `awb_on_low_saturation`
- `format_bgr888_awb_on` *(Picamera2 only)*
- `format_rgb888_awb_on` *(Picamera2 only)*
- `format_xbgr8888_awb_on` *(Picamera2 only)*

For each case it saves:
- a JPEG capture
- requested settings
- resulting PiServer config
- backend diagnostics/metadata in `manifest.json`

### 3) Added backend diagnostics helper
Extended `CameraService` with a diagnostics method that records:
- current PiServer camera config
- FPS
- raw frame age
- Picamera2 controls/properties/metadata when available
- OpenCV capture readback info when using OpenCV fallback

### 4) Version bump
Updated `APP_VERSION` from `0_4_7` to `0_4_8`.

## How to run the new diagnostic tool on the Pi
From the PiServer folder:

```bash
python run_camera_settings_diagnostic.py
```

Optional:

```bash
python run_camera_settings_diagnostic.py --no-format-sweep
python run_camera_settings_diagnostic.py --warmup 1.2
```

After it finishes, review the newest folder under:

```bash
PiServer/data/camera_diagnostics/
```

Key files:
- `manifest.json`
- `01_*.jpg`, `02_*.jpg`, ...

## Verification actually performed
Ran locally in the uploaded PiDrive repo copy after patching forward from `0_4_7`.

### Checks run
1. Python syntax check:
   - `python3 -m py_compile piserver/app.py piserver/services/camera_service.py piserver/tools/camera_diagnostic.py run_camera_settings_diagnostic.py tests/test_camera_service.py tests/test_camera_diagnostic.py`
2. Full PiServer unit tests:
   - `python3 -m unittest discover -s tests -q`

### Result
- `26 tests passed`

## Notes / limits
- This patch adds a focused test utility and fixes a real AWB wiring bug, but it does **not** claim the red-tint issue is fully solved yet.
- The diagnostic images and `manifest.json` are intended to show whether the tint changes with AWB, saturation, or Picamera2 format selection.
- No snapshot-folder logic from `0_4_5` to `0_4_7` was removed.
