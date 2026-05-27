# PiSD 0.9.0 Patch / Stable Package Notes

## Request summary

The user asked for Manual Drive keyboard control and also asked to package the result as v9 and as a v9 patch.

Requested keyboard behaviour:

- Allow the user to control the car from the keyboard.
- `Arrow Up` / `Arrow Down` adjust live speed/throttle by `0.05` once per press.
- Holding `Arrow Left` / `Arrow Right` continuously increases steering toward the selected side by full scale in `0.5 s`.
- Preserve the current linear X steering model, intended motor output display, overlay settings sidecars, and cleaned Motor Tuning page state.

## Cause / root cause

Manual Drive previously supported pointer/drag-pad control only. This meant a keyboard-only workflow could not drive the car while watching the live camera overlay. The new keyboard path needed to share the same backend safety and recording behaviour as the drag pad instead of adding a separate motor path.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_0.md`

## Behaviour changed

### Manual Drive keyboard control

Manual Drive now listens for keyboard controls when the page is not focused inside an editable field or the Manual visual tuning popup:

| Key | Behaviour |
|---|---|
| `Arrow Up` | Increase live throttle by `+0.05` once per key press |
| `Arrow Down` | Decrease live throttle by `-0.05` once per key press |
| Hold `Arrow Left` | Ramp steering toward `-1.00` at full scale in `0.5 s` |
| Hold `Arrow Right` | Ramp steering toward `+1.00` at full scale in `0.5 s` |
| `Space` | STOP motors and clear keyboard throttle/steering |

Keyboard control is still locked until the Manual Drive motor-output safety checkbox is enabled.

### Shared motor command path

Keyboard commands use the same endpoint as the drag pad:

```text
POST /api/control/manual
```

This preserves:

- backend safety acknowledgement checks;
- saved max-speed limit enforcement;
- intended motor output readouts;
- linear X steering;
- recording labels using the same steering/throttle values;
- page-leave motor fail-safe behaviour.

### UI feedback

The Manual Drive control panel now includes a small keyboard help block and live keyboard status text. The existing steering/throttle readout and knob position update from keyboard input as well as pointer input.

### Stable v9 package promoted

The package version is now:

```text
0.9.0
```

`README.md` and `docs/STABLE_BASELINE.md` now describe `PiSD_0_9_0` as the current full stable package. Future PiSD patches after this package should use the `0_9_x` patch line unless a newer stable baseline is promoted.

## Preserved behaviour / rollback check

Before finalising, the latest accepted patch notes were reviewed:

- `0_8_9`: grouped Manual visual tuning / Overlay calibration popup.
- `0_8_10`: removed old min/max caps from overlay calibration values.
- `0_8_11`: saved `overlay_settings.json` and `overlay_settings_history.jsonl` into recording/snapshot folders.

Confirmed this update does not roll back:

- linear X steering;
- removal of `turn_gain` from real motor steering;
- removal of motor `turn_curve` from real motor steering;
- removal of Manual Drive steer strength;
- intended motor output display;
- motor start dead-zone kick backend/settings;
- reset/blank Motor Tuning page from `0_8_7`;
- reduced seven-control Manual Drive overlay schema;
- uncapped Manual visual tuning values;
- recording/snapshot overlay settings sidecar files for piTrainer.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Manual Drive static test confirms keyboard instructions/status are present.
- Manual Drive static test confirms keyboard JS contains `KEYBOARD_THROTTLE_STEP`, `KEYBOARD_STEERING_FULL_SCALE_MS`, arrow-key handlers, and `requestAnimationFrame` steering ramp logic.
- Motor steering test still confirms linear X steering and intended-output behaviour.
- Settings persistence test still confirms legacy `turn_gain`, motor `turn_curve`, and Manual Drive `steer_strength` are ignored/removed.
- Recording service test still confirms `overlay_settings.json` and `overlay_settings_history.jsonl` are saved for trainer reuse.
- Standard validation passed in static/simulation mode.
- `PiSD.py --status-only` completed successfully in simulation mode.

## Verification not performed / known limits

- Hardware keyboard driving was not tested on a real Raspberry Pi car in this container.
- Real Raspberry Pi camera preview was not hardware-tested here.
- Real Raspberry Pi motor movement was not hardware-tested here.
- Full Flask browser-route testing was not run here because this container environment does not include Flask.

## Suggested Pi-side test sequence

1. Apply `PiSD_0_9_0_patch.zip` over the current `PiSD_0_8_11` state, or install the full `PiSD_0_9_0.zip` package.
2. Start PiSD:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/manual-drive`.
4. Lift the wheels and tick the motor-output safety checkbox.
5. Test keyboard control:
   - press `Arrow Up` once and confirm throttle increases by `0.05`;
   - press `Arrow Down` once and confirm throttle decreases by `0.05`;
   - hold `Arrow Right` for about `0.5 s` and confirm steering reaches about `+1.00`;
   - hold `Arrow Left` to ramp back left;
   - press `Space` and confirm motors stop and readouts return to zero.
6. Confirm drag-pad control still works and recording labels still save normal steering/throttle values.
