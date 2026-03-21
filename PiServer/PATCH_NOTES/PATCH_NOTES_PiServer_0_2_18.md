# PiServer 0_2_18 Patch Notes

## Summary
This patch updates the current PiServer web UI on top of the uploaded repo base. It removes the old on-screen quick-drive arrows, restyles recording to match the safety toggle style, and adds saved steering-bias tuning to the runtime controls.

## User-reported issues addressed
1. The Manual Drive panel still had on-screen arrow buttons that duplicated joystick and keyboard input.
2. The Recording control looked inconsistent compared with the safety controls.
3. Runtime tuning could not trim steering bias without going into motor-side wiring/bias settings.

## Changes made
- Removed the Forward / Reverse / Left / Right quick-drive buttons from the Manual Drive panel.
- Removed the duplicate manual speed slider from the Manual Drive panel.
- Kept Stop in Manual Drive and converted E-Stop into a single toggle-style button.
- Converted the Recording control into a toggle-style button with matching visual behavior.
- Added a saved `steer_bias` runtime parameter and exposed it as a slider in Runtime Tuning.
- Applied `steer_bias` in the control loop before motor mixing so it trims steering response across runtime driving modes.
- Persisted `steer_bias` through save/reload config.
- Added a Status metric for live steering bias.
- Bumped app/static version to `0_2_18` so browsers refresh the updated web assets.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/tests/test_control_service.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_18.md`

## Notes
- This patch is based on the current uploaded PiDrive repo snapshot, which still uses the older panel layout. It does not assume the earlier speculative UI patches were already installed on the Pi.
- `steer_bias` is a runtime steering trim and is separate from left/right motor bias.
