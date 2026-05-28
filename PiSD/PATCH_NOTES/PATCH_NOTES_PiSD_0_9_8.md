# PiSD 0.9.8 Patch Notes

## Request summary

The user reported that steering on the Raspberry Pi seemed to stay stuck on a positive value.

This patch builds forward from the accepted `PiSD_0_9_7` state and does not restore the removed motor dead-zone/start-kick feature.

## Cause / root cause

A stale frontend reference remained after the `0.9.7` dead-zone cleanup:

```javascript
motorStartSettingsPopup
```

That popup was removed, but `manual_drive.js` still referenced it inside the keyboard-control blocking check. In a browser, reading an undeclared variable can throw a `ReferenceError` during keyboard handling. On the Pi this could make keyboard steering state unreliable and could leave a previously positive steering command visible or active until another stop/refresh path corrected it.

The keyboard steering path also depended on receiving a normal left/right `keyup`. If Chromium or the page lost focus while a right-arrow key was active, the held-key flag could remain set and continue ramping/holding positive steering.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_8.md`

## Behaviour changed

### Removed stale dead-zone popup reference

Manual Drive keyboard handling no longer references the removed motor-start dead-zone popup. The blocking check now only checks the remaining Manual visual tuning popup and editable fields.

### More reliable keyboard steering release

Added a shared release helper:

```javascript
releaseKeyboardSteeringToCentre()
```

This clears both left/right held-key flags and returns steering to `0` over the current `0.8 s` timing.

The release helper is now called when:

- the left/right arrow key is released;
- the browser window loses focus;
- the page becomes hidden.

This makes the Pi-side browser less likely to keep a stale positive steering value if a `keyup` event is missed.

## Behaviour preserved / rollback check

Checked against the latest patch and previous 3 patch notes:

- `0_9_7`: motor dead-zone/start-kick backend and UI remain removed.
- `0_9_6`: AI drive responsiveness diagnostics and TFLite output dequantization are preserved.
- `0_9_5`: TFLite NumPy tensor shape loading fix is preserved.
- `0_9_4`: AI load diagnostics and runtime visibility are preserved.

Confirmed this patch does not restore:

- `turn_gain` in real motor steering;
- motor `turn_curve` in real motor steering;
- Manual Drive steer strength;
- old Motor Tuning panels;
- capped Manual visual tuning overlay values;
- motor start dead-zone/kick logic.

## Verification actually performed

Applied locally on top of:

```text
PiSD_0_9_0 + 0_9_1 + 0_9_2 + 0_9_3 + 0_9_4 + 0_9_5 + 0_9_6 + 0_9_7
```

Then ran:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/test_ai_drive_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All listed checks passed in the local static/simulation environment.

## Not verified here

- Real Raspberry Pi browser keyboard events.
- Real GPIO motor movement.
- Real camera preview.
- Full Flask route tests, because this container environment does not include the Pi-side Flask runtime dependencies.
- Real TensorFlow/TFLite inference on the Pi.

## Suggested Pi-side test after applying

1. Restart PiSD.
2. Hard refresh the browser tab on the Pi / control device.
3. Open Manual Drive and enable motor output with wheels lifted.
4. Hold Right arrow until steering becomes positive.
5. Release Right arrow and confirm steering returns to `0` over about `0.8 s`.
6. Repeat for Left arrow.
7. Click away from the browser or switch tab while steering is active; steering should release toward `0` instead of staying positive.
