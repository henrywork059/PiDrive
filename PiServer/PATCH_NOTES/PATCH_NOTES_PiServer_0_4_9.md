# PATCH NOTES — PiServer_0_4_9

## Baseline
- Stable baseline: `PiServer_0_4_0`
- Previous active patch: `0_4_8`
- This patch is built forward on top of the accepted `0_4_5` to `0_4_8` snapshot, steering, and camera-diagnostic work.
- No recent `0_4_x` UI/style/status fixes were removed.

## Request summary
After running the `0_4_8` camera diagnostic on the Pi, the reported result was:
- almost every diagnostic image still looked red-tinted
- `force_awb_off` looked best, but still not fully correct

Requested next step:
- patch the camera testing/diagnostic path so PiServer can test deeper camera settings related to tint / white balance

## Findings from the current result
The earlier `0_4_8` diagnostic already showed that changing Picamera2 output format alone was not enough.
The new user result points more strongly to a white-balance / colour-gain tuning problem than to a simple snapshot-folder or repeat-frame bug.

A likely next test surface is:
- keep `AWB` off
- apply manual `ColourGains` through Picamera2
- compare several red/blue gain pairs in a controlled sweep

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/tools/camera_diagnostic.py`
- `PiServer/run_camera_settings_diagnostic.py`
- `PiServer/tests/test_camera_service.py`
- `PiServer/tests/test_camera_diagnostic.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_9.md`

## Exact changes made
### 1) Added manual colour-gain support to PiServer camera settings
Updated `piserver/services/camera_service.py` so PiServer now supports manual white-balance gain values:
- `color_gain_red`
- `color_gain_blue`

Also added compatibility aliases:
- `colour_gain_red`
- `colour_gain_blue`
- `red_gain`
- `blue_gain`

When `auto_white_balance` is off, PiServer now applies:
- `ColourGains = (color_gain_red, color_gain_blue)`

through Picamera2 controls.

### 2) Expanded the camera diagnostic sweep
Updated `piserver/tools/camera_diagnostic.py` so the diagnostic can now run a manual gain sweep when Picamera2 is active.

New comparison cases include:
- `awb_off_rg075_bg115`
- `awb_off_rg070_bg120`
- `awb_off_rg065_bg125`
- `awb_off_rg060_bg130`

These are designed to progressively reduce red gain and raise blue gain while keeping AWB disabled.

### 3) Added CLI control for the new sweep
Updated the diagnostic entry point so you can now skip manual gain cases if needed:

```bash
python run_camera_settings_diagnostic.py --no-manual-gain-sweep
```

Default behavior now includes both:
- the earlier format sweep
- the new AWB-off manual gain sweep

when Picamera2 is the active backend.

### 4) Version bump
Updated `APP_VERSION` from `0_4_8` to `0_4_9`.

## How to run the updated diagnostic on the Pi
From the PiServer folder:

```bash
python run_camera_settings_diagnostic.py
```

Optional:

```bash
python run_camera_settings_diagnostic.py --no-format-sweep
python run_camera_settings_diagnostic.py --no-manual-gain-sweep
python run_camera_settings_diagnostic.py --warmup 1.2
```

The output still goes to:

```bash
PiServer/data/camera_diagnostics/<timestamp>/
```

## What to look for in the new results
The most useful comparison is likely between:
- `force_awb_off`
- `awb_off_rg075_bg115`
- `awb_off_rg070_bg120`
- `awb_off_rg065_bg125`
- `awb_off_rg060_bg130`

If one of those manual-gain images looks clearly closer to real colour, that strongly suggests the remaining red cast is mainly a white-balance tuning issue rather than a file-save or repeated-frame bug.

## Verification actually performed
Ran locally in the patched PiServer repo copy:

1. Python syntax check:
   - `python3 -m py_compile piserver/app.py piserver/services/camera_service.py piserver/tools/camera_diagnostic.py run_camera_settings_diagnostic.py tests/test_camera_service.py tests/test_camera_diagnostic.py`
2. Full PiServer unit tests:
   - `python3 -m unittest discover -s tests -q`

## Result
- All tests passed locally after the patch.

## Known limits / notes
- This patch improves the diagnostic/testing path and adds a real Picamera2 control surface for manual colour gains.
- It does **not** claim the camera tint is fully solved yet.
- No snapshot, recorder, reverse-steering, or recent UI layout/style fixes were removed by this patch.
