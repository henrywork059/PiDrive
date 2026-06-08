# PiSD 0.10.1 Patch Notes

## Request summary

Review the Start camera / Live stream controls and simplify them so the user only needs one button to start the camera and show the live preview.

Also update Manual Drive keyboard shortcuts so:

- `r` toggles recording;
- `s` saves a snapshot.

This patch builds forward from the accepted `PiSD_0_10_0` stable v10 baseline.

## Cause / root cause

`PiSD_0_10_0` already combined the AI Mode camera/live action, but Manual Drive still had two adjacent user-facing controls:

- `Start camera` for camera service / snapshot refresh;
- `Live stream` for MJPEG preview.

The legacy Dashboard and Testing Server preview controls also still exposed separate camera-start and live-preview actions. This made the camera workflow more complicated than needed and could cause confusion about which button should be used before driving or recording.

Manual Drive already had click buttons for recording and snapshots, but keyboard shortcuts were limited to driving and STOP controls.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/static/js/testing_server.js`
- `PiSD/pisd/web/static/js/panel_testing.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/scripts/test_testing_server_gui.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TESTING_SERVER_GUI.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_1.md`

## Behaviour changed

### One camera/live start action

Manual Drive now has one preview-start button:

```text
Start camera + live
```

That button calls `POST /api/camera/start`, then switches the preview image to `/video_feed`.

The old Manual Drive `Start camera` still-preview button was removed from the user-facing Camera panel. The existing `Capture frame` button remains the way to save a still snapshot.

The legacy Dashboard camera preview panel now also keeps only:

```text
Start camera + live
Stop camera only
```

The old Dashboard `Show live stream` button was removed.

The Testing Server preview card now uses a single `Start camera + live` button for the combined start-and-MJPEG path, while keeping `Snapshot frame` as a separate diagnostic still-frame action.

AI Mode was already using a combined camera/live button in `0.9.10`; this patch preserves that accepted behaviour.

### Manual Drive keyboard shortcuts

Manual Drive now supports these recording/capture shortcuts when focus is not inside a text input/select/textarea and the overlay popup is not open:

```text
r = toggle recording
s = save snapshot
```

The shortcuts call the same existing functions as the visible buttons:

- `r` calls `toggleRecording()`;
- `s` calls `captureFrame()`.

Existing keyboard drive controls are preserved:

```text
↑ / ↓ = throttle step
hold ← / → = steering ramp
Space = STOP
```

### Documentation and tests updated

The README, stable-baseline notes, testing GUI guide, and test plan now describe the one-button camera/live workflow and the new Manual Drive `r` / `s` shortcuts.

Static contract tests were updated so future changes should not accidentally restore the older separate Start camera / Live stream pair on the main control pages.

## Preserved behaviour / rollback safety

Checked against the latest patch note and previous accepted notes:

- `0_10_0`: stable v10 baseline is preserved and used as the build-forward source.
- `0_9_10`: AI Mode combined camera/live control, AI recording/snapshot controls, and AI update-loop improvements are preserved.
- `0_9_9`: AI runtime install guidance and helper scripts are preserved.
- `0_9_8`: keyboard steering release/focus handling is preserved.
- `0_9_7`: removed motor dead-zone/start-kick UI/backend logic remains removed.

This patch does not change motor steering math, overlay geometry, recording backend storage, camera backend settings, AI model loading, or runtime config schema.

## Verification actually performed

Applied locally on top of the uploaded `PiSD_0_10_0.zip`, then ran:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/main_dashboard.js
node --check pisd/web/static/js/testing_server.js
node --check pisd/web/static/js/panel_testing.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_testing_server_gui.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All listed checks passed in this container.

## Not verified here

- Real Raspberry Pi camera preview in Chromium.
- Real keyboard input through the Pi browser.
- Real snapshot file creation from camera hardware.
- Real recording sessions on the Pi filesystem.
- Real motor movement.

## Suggested Pi-side check after applying

1. Restart PiSD and hard-refresh the browser.
2. Open Manual Drive.
3. Click `Start camera + live` and confirm the live MJPEG preview appears.
4. Press `s` and confirm a snapshot is saved.
5. Press `r` once and confirm `REC on`; press `r` again and confirm recording stops.
6. Confirm the old separate `Start camera` / `Live stream` pair is no longer shown in Manual Drive.
