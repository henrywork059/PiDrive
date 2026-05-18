# PiSD 0.6.7 Patch Notes

## Request summary
Record the current Manual Drive visual path overlay settings with screenshots and recording sessions so piTrainer can redraw the same overlay later instead of relying on whatever settings happen to be active in the trainer.

## Cause / root cause
PiSD already saved camera, motor, steering, throttle, and trainer-friendly labels beside each captured frame. After the v0.6.3 to v0.6.6 overlay work, however, the overlay became highly configurable and those visual tuning values were not saved with the data. A trainer could load the frame and steering/throttle labels, but it could not know the exact `curve_strength`, width, projection, opacity, sample count, or other overlay settings used at the time of capture.

This made overlay redraw in piTrainer ambiguous, especially after overlay settings were changed from sliders to unclamped number inputs in v0.6.5 and v0.6.6.

## Files changed
- `pisd/__init__.py`
- `pisd/app.py`
- `pisd/services/recording_service.py`
- `pisd/web/static/js/manual_drive.js`
- `docs/RECORDING_DATA.md`
- `scripts/test_recording_service.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_6_7.md`

## Exact behaviour changed
- The Manual Drive page now sends the currently applied overlay settings when the user captures a single screenshot.
- The Manual Drive page now sends the currently applied overlay settings when the user starts a continuous recording session.
- `RecordingService` can now receive a runtime settings provider from the app and read the latest saved Manual Drive overlay settings while recording.
- Single-capture `manifest.json` now stores:
  - `overlay_settings`
  - `overlay_settings_source`
  - `overlay_schema_version`
- Continuous-recording `manifest.json` now stores the session/latest overlay settings and declares the overlay metadata in the schema.
- Every full `records.jsonl` frame record now stores:
  - `overlay_settings`
  - `overlay_settings_source`
  - `overlay_schema_version`
- Every compact `labels.jsonl` training row now stores:
  - `overlay_settings`
  - `overlay_schema_version`
- The saved overlay settings are JSON-safe snapshots and keep finite user-entered numeric values without restoring the old slider clamps.
- Updated `docs/RECORDING_DATA.md` to document how piTrainer should find overlay metadata.
- Updated `scripts/test_recording_service.py` to verify overlay settings are present in capture records, recording records, and `labels.jsonl`.
- Updated `pisd.__version__` to `0.6.7`.

## Compatibility notes
- Existing recordings remain readable. Older sessions simply will not have `overlay_settings`; piTrainer should fall back to current/default overlay settings when the field is absent.
- The new fields are additive only. Existing `records.jsonl` and `labels.jsonl` keys are preserved.
- Overlay metadata is visual-only. It does not change motor output, AI output, camera settings, recording FPS, or saved steering/throttle labels.
- The recording service preserves unclamped finite overlay values as metadata, but still discards non-JSON-safe/unserialisable values.

## Rollback-risk checks
Reviewed the latest PiSD patch notes before editing:
- `0_6_6`: popup overlay settings, unclamped overlay numbers, advanced overlay values.
- `0_6_5`: number inputs replacing sliders.
- `0_6_4`: corrected left/right overlay direction.
- `0_6_3`: shared overlay helper, filled road corridor, smoother perspective/turn geometry.

Confirmed this patch does not modify the shared overlay geometry, overlay popup controls, left/right direction, Manual Drive backend speed/safety cleanup, AI steering-only fixed-throttle behaviour, camera defaults, or recording folder layout.

## Verification actually performed
- Applied `PiSD_0_6_1_patch.zip` through `PiSD_0_6_6_patch.zip` onto a clean `PiSD_0_6_0.zip` working tree before making this patch.
- `python3 -m py_compile pisd/services/recording_service.py pisd/app.py scripts/test_recording_service.py`
- `python3 -m compileall -q pisd scripts PiSD.py`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/overlay_geometry.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `python3 scripts/test_recording_service.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Real Raspberry Pi camera/motor hardware tests were not run in this container.
- Real browser capture/recording interaction was not tested on the target Pi display.
- piTrainer redraw integration was not patched in this package; this patch only ensures PiSD records the metadata needed by piTrainer.

## Known limits / next steps
- If overlay settings are changed in the Manual Drive popup but not applied, PiSD records the currently applied overlay settings, not the un-applied draft values still sitting in the popup fields.
- Continuous recording reads the latest saved overlay settings through the settings provider. The Manual Drive frontend also sends the applied overlay settings at recording start for a precise starting snapshot.
- The next piTrainer patch should prefer `labels.jsonl[*].overlay_settings`, then `records.jsonl[*].overlay_settings`, then `manifest.json.overlay_settings`, and only then fall back to trainer defaults.
