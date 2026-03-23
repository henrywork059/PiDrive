# CustomDrive 0_1_3 Patch Notes

## Goal
Fix the GUI launch confusion on the Pi, keep CustomDrive easier to manage, and make the live path rely more clearly on PiServer code.

## Problems found
1. `python run_custom_drive_gui.py` could appear to do nothing because there were no explicit startup prints before Flask began serving.
2. It was not obvious from the GUI whether live mode was really using PiServer services or whether real GPIO motor output was available.
3. CustomDrive live settings and PiServer runtime settings could drift apart, making maintenance harder.
4. JSON settings writes were not atomic.

## Changes made
- Added `custom_drive/piserver_integration.py` to centralize PiServer imports and runtime config syncing.
- Live runtime now explicitly imports and uses PiServer `CameraService` and `MotorService` through that helper.
- Live runtime now syncs `camera`, `motor`, and `runtime.steer_mix` into `PiServer/config/runtime.json` after saving settings.
- Added service-state reporting in the GUI status panel:
  - PiServer services state
  - service detail text
  - `gpio_available` from PiServer `MotorService`
- Added a **Rebuild Runtime** GUI button to re-create the runtime after changing settings or reconnecting hardware.
- Added clear terminal startup messages and browser URLs in `run_custom_drive_web.py` / `run_custom_drive_gui.py`.
- Disabled Flask auto-reloader to avoid duplicate confusing startup behaviour.
- Made `run_settings.json` and `runtime_settings.json` writes atomic.

## Important behaviour after this patch
- The GUI launcher now prints where to open the browser.
- In live mode, the real motors are still driven by PiServer `MotorService.update(...)`.
- The mission only drives the motors after you press **Start Auto** or use the headless runner.
- When `gpio_available` is `false`, the PiServer motor service is in simulation/fallback mode, so no real GPIO output will happen.

## Changed files
- `CustomDrive/custom_drive/piserver_integration.py`
- `CustomDrive/custom_drive/live_runtime.py`
- `CustomDrive/custom_drive/runtime_settings.py`
- `CustomDrive/custom_drive/run_settings.py`
- `CustomDrive/custom_drive/web_app.py`
- `CustomDrive/custom_drive/web/templates/index.html`
- `CustomDrive/custom_drive/web/static/app.js`
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/run_custom_drive_gui.py`
- `CustomDrive/README.md`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_3.md`

## Verification performed
- `python -m compileall CustomDrive`
- simulated import/runtime creation smoke test on the patched files

## Remaining limits
- I could not verify real GPIO switching or Pi camera behaviour inside this container.
- A real live run still depends on your Pi having the PiServer dependencies available (`RPi.GPIO`, camera stack, Flask, NumPy/OpenCV if needed).
