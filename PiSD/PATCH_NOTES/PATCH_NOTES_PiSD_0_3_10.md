# PiSD 0.3.10 Patch Notes

## Request summary

The user requested a focused Manual Drive UI patch after testing `PiSD_0_3_9_patch`:

- reduce the drag-pad ball size by 50%;
- remove the `Snapshot view` button from the camera preview panel because it is not useful;
- update the compact Status / Run signals panel so it also shows the current intended drive command sent to the motors and the actual left/right motor outputs currently being reported by the motor service.

## Cause / root cause

- The drag knob remained visually large after the drag-pad alignment fixes, which made precise control harder on smaller screens.
- The preview panel had both `Start camera`, `Live stream`, and `Snapshot view`; after `Start camera` and `Live stream` were separated, the extra `Snapshot view` button added clutter without clear user value.
- The compact status strip showed hardware, camera, motor, FPS, and recording status, but not the most important live driving values: intended steering/throttle and actual mapped motor outputs.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/static/css/pisd_design_system.css`
- `PiSD/pisd/web/static/css/pisd_layout_system.css`
- `PiSD/pisd/web/static/css/unified_layout.css`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_10.md`

## Behaviour changed

### Manual Drive drag pad

- The drag-pad knob diameter is reduced from 56 px to 28 px.
- The knob keeps the existing pointer-relative positioning logic.
- Shared/final CSS layers also define the smaller knob size so later shared stylesheet ordering does not silently restore the older large knob.

### Preview panel buttons

- Removed the `Snapshot view` button from the Manual Drive preview panel.
- `Start camera` remains as the still/snapshot camera-start action.
- `Live stream` remains the action that starts the camera if needed and switches the preview to `/video_feed`.
- Capture and recording buttons remain unchanged.

### Status / Run signals panel

The compact status strip now includes:

- `HW`
- `Cam`
- `Motor`
- `FPS`
- `Rec`
- `Cmd` — intended command: steering and throttle values sent from the drag pad;
- `Out` — actual motor output values returned/reported by the motor service: left and right.

During drag-pad use:

- `Cmd` updates immediately from the pointer-derived steering/throttle command.
- `Out` updates after `/api/control/manual` returns the mapped left/right outputs.
- STOP resets both command and output values to zero after `/api/control/stop`.
- Refresh/status calls also repopulate the values from `motor.last_command`, `motor.last_left`, and `motor.last_right`.

## Compatibility / migration notes

- No camera backend behaviour changed.
- No motor service mapping logic changed.
- No recording service logic changed.
- No settings schema changed.
- This patch is UI-only except for version and validation updates.

## Verification performed

Executed locally in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_responsive_layout_contract.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Observed results:

- Python compile check passed.
- `PiSD.py --status-only` returned `PISD-OK-000`.
- error-reporting check passed.
- Manual Drive static/source contract passed, including:
  - `Snapshot view` button removed;
  - intended/output motor signal readouts present;
  - smaller drag knob token present;
  - semantic status-before-preview layout still present.
- UI presentation consistency check passed.
- responsive layout contract check passed.
- standard validation passed with API/camera/motor skipped.

## Not verified here

- Real Pi browser rendering.
- Live Flask route execution in a browser.
- Real camera/motor output on hardware.

## Pi-side test instructions

After applying this patch, hard refresh the browser and open:

```text
http://<pi-ip>:5050/manual-drive
```

Check:

1. the drag-pad ball is about half the previous diameter;
2. the preview panel no longer has a `Snapshot view` button;
3. `Start camera` and `Live stream` still work;
4. `Cmd` changes while dragging the pad;
5. `Out` changes after the motor API response;
6. pressing any STOP button returns `Cmd` and `Out` to zero.
