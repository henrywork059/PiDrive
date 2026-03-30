# PATCH NOTES — PiServer_0_4_10

## Baseline
- Stable baseline: `PiServer_0_4_0`
- Previous active patch: `0_4_9`
- This patch is built forward on top of the accepted `0_4_5` to `0_4_9` snapshot, steering, and camera-diagnostic fixes.
- No recent `0_4_x` UI/style/status fixes were removed.

## Request summary
The camera diagnostic results showed a clear winner:
- `force_awb_off` produced the correct image
- every other diagnostic image remained wrong

Requested next step:
- turn that diagnostic result into the real PiServer camera default without rolling back earlier fixes

## Root cause / interpretation
The diagnostic sweep strongly indicates that, on this PiServer camera setup, automatic white balance is the wrong default for normal live operation.

The earlier diagnostic work did its job:
- output-format changes were not the real fix
- manual colour-gain sweeps were not needed
- plain `AWB off` matched the correct image

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/config_store.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/tests/test_camera_service.py`
- `PiServer/tests/test_config_store.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_10.md`

## Exact changes made
### 1) Changed PiServer camera default to AWB off
Updated PiServer defaults so `auto_white_balance` now defaults to `False` in:
- `piserver/core/config_store.py`
- `piserver/services/camera_service.py`

Result:
- new/default PiServer camera config now starts from the same setting that the diagnostic proved correct
- existing explicit saved camera settings are still preserved by config merge logic

### 2) Updated the active Camera page default checkbox
Updated the active UI template so the Camera page checkbox for **Auto white balance** is no longer rendered as checked before config loads.

This keeps the visible default aligned with the actual backend default.

### 3) Version bump
Updated `APP_VERSION` from `0_4_9` to `0_4_10` for cache-busting after file replacement.

## Resulting behavior
After applying this patch:
- PiServer defaults to **AWB off** for the live camera path
- if the runtime config does **not** already explicitly force AWB on, the camera should come up with the corrected colour by default
- users can still manually turn AWB back on from the Camera page if they ever need to

## Verification actually performed
Ran locally in the patched PiServer repo copy:
1. Python syntax check:
   - `python3 -m py_compile piserver/app.py piserver/core/config_store.py piserver/services/camera_service.py tests/test_camera_service.py tests/test_config_store.py`
2. Full PiServer unit tests:
   - `python3 -m unittest discover -s tests -q`

## Result
- All tests passed locally after the patch.

## Important note for existing saved settings
This patch changes the PiServer default.

If the Pi already has a saved camera config in `config/runtime.json` with:
- `camera.auto_white_balance = true`

that explicit saved value will still win, by design.
In that case, uncheck **Auto white balance** once in the Camera page and click **Apply + restart** so the corrected setting is saved.

## Known limits / notes
- This patch intentionally does **not** remove the diagnostic tooling from `0_4_8` and `0_4_9`; it simply applies the proven result as the default runtime behavior.
- No snapshot-folder, repeated-snapshot, reverse-steering, or recent UI layout/style fixes were removed.
