# PiSD 0.9.7 Patch Notes

## Request summary

Remove the current motor dead-zone / start-kick feature and related UI from PiSD.

This patch builds forward from the accepted `PiSD_0_9_6` state. It preserves the recent AI runtime fixes, model upload/delete flow, keyboard steering timing, linear steering, intended motor-output display, and saved overlay settings behaviour.

## Cause / reason for change

The motor start dead-zone kick had been added as an experimental helper for static friction. The latest direction is to remove that logic for now so motor output is simpler and easier to debug:

- requested motor output should be sent directly;
- there should be no temporary hidden hardware boost;
- Manual Drive and Settings should not expose dead-zone/kick controls;
- old saved dead-zone/kick keys should not continue to appear in normalised settings.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/config/defaults.json`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/scripts/test_motor_steering_modes.py`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_7.md`

## Behaviour changed

### Removed from backend motor output

The following motor config keys are no longer part of `MotorConfig`:

- `start_deadzone`
- `start_kick_seconds`

The temporary timer-based kick path was removed from `MotorService.update()`. Motor output now follows the normal mapping directly:

```text
steering/throttle input
→ linear turn-rate mapping
→ logical tuning / max speed / bias
→ hardware direction mapping
→ motor driver output
```

There is no hidden start boost between mapping and hardware output.

### Removed from Manual Drive

The Manual Drive page no longer renders:

- `Motor start dead-zone` button;
- motor dead-zone popup;
- `Start dead-zone` input;
- `Kick seconds` input;
- dead-zone apply/reset handlers.

The remaining Manual Drive controls are unchanged: drag pad, keyboard control, stop buttons, live overlay, file management, and Manual visual tuning.

### Removed from Settings page

The Settings page motor form no longer exposes:

- `Start dead zone`;
- `Kick seconds`.

### Runtime settings compatibility

Existing `runtime_settings.json` files may still contain old keys. `SettingsManager` now removes these old keys during normalisation so they are not surfaced back to the UI/service.

### Preserved behaviour

This patch does not change:

- linear X steering;
- `turn_gain` removal;
- `turn_curve` removal from real motor steering;
- intended motor output display;
- AI model upload/delete/load diagnostics;
- TFLite loading fixes through `0.9.6`;
- keyboard steering `0.8 s` ramp and return-to-centre;
- overlay calibration and recording/snapshot overlay settings export.

## Verification actually performed

Applied locally on top of:

```text
PiSD_0_9_0 + 0_9_1 + 0_9_2 + 0_9_3 + 0_9_4 + 0_9_5 + 0_9_6
```

Then ran:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/settings_tab.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All listed checks passed in the local static/simulation environment.

## Not verified here

- Real GPIO motor movement on Raspberry Pi hardware.
- Real camera preview on Raspberry Pi hardware.
- Full Flask route tests, because this container environment does not include the Pi-side Flask runtime dependencies.
- Real TensorFlow/TFLite inference on the Pi.

## Known limits / next steps

- If the real motors still need extra torque at startup, the next approach should be designed separately, preferably with clearer visible diagnostics and not hidden inside the normal motor-output path.
- Any old local browser cache may still have previous JavaScript until the browser reloads the updated static asset version. Restart PiSD and hard-refresh the browser after applying.
