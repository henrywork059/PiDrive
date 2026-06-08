# PiSD 0.10.2 Patch Notes

## Request summary

Update the Manual Drive and AI Mode UI labels and colours after the `0.10.1` camera/live simplification.

Requested changes:

- colour the Manual Drive and AI Mode buttons in green;
- rename the AI Mode `Start camera + live stream` button;
- remove the unneeded AI Mode `Refresh frame` button;
- shorten the snapshot and recording button labels;
- review the panel title names in AI Mode and Manual Drive.

This patch builds forward from the uploaded `PiSD_0_10_0` stable v10 baseline plus the accepted `PiSD_0_10_1` patch.

## Cause / root cause

`0.10.1` correctly reduced camera/live startup to one main action, but several labels were still longer than needed:

- AI Mode still showed `Start camera + live stream`, while Manual Drive showed `Start camera + live`.
- AI Mode still exposed a separate `Refresh frame` button, which duplicated the old still-preview refresh behaviour and was no longer needed for the simplified live workflow.
- AI Mode used longer recording labels such as `Start recording` / `Stop recording`.
- Manual Drive still used `Capture frame`, although the keyboard shortcut and user wording now call the action a snapshot.
- Some panel titles were accurate but wordy or inconsistent between Manual Drive and AI Mode.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/css/front_page.css`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/test_front_page_tabs.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_2.md`

## Behaviour changed

### Shorter Manual Drive camera controls

Manual Drive now uses these shorter labels:

```text
Start live
Snapshot
Record
```

The existing behaviour is preserved:

- `Start live` still calls `POST /api/camera/start`, then switches the preview to `/video_feed`.
- `Snapshot` still calls the same capture path as before and stores overlay metadata.
- `Record` still toggles the same recording service path.
- Keyboard shortcuts from `0.10.1` are preserved: `s` saves a snapshot and `r` toggles recording.

### AI Mode camera controls

AI Mode now uses the same shorter live/snapshot/record wording:

```text
Start live
Snapshot
Record
```

The old AI Mode `Refresh frame` button was removed from the UI and the `aiSnapshot` JavaScript binding was removed. The remaining `Snapshot` button still uses `POST /api/recording/capture` through the existing shared recording service.

While recording in AI Mode, the toggle now changes to:

```text
Stop rec
```

instead of the longer `Stop recording`.

### Green current-workflow buttons

The front page Manual Drive and AI Mode cards are now highlighted in green to make the two main driving workflows stand out.

The Manual Drive / AI Mode live and snapshot action buttons also use a green action style so they are visually distinct from neutral secondary controls.

### Panel title review

Manual Drive panel names were shortened and made more direct:

- `Status / Run signals` → `Status / Live signals`
- `Camera / Live view` → `Camera / Live camera`
- `Drag Pad / Manual control` → `Drive input / Manual steering`
- `Safety / Emergency stop` → `Safety / Motor stop`
- `Files / Recordings & snapshots` → `Saved data / Records & snaps`

AI Mode panel names were shortened and made more consistent:

- `Camera / AI prediction preview` → `Camera / Live AI preview`
- `Model / Load trained model` → `AI model / Model file`
- `Safety layer / AI → safety limiter → motors` → `Safety / Output limiter`
- `Run / Preview before drive` → `AI output / Prediction readout`
- `Status / AI mode log` → `Log / AI actions`

## Preserved behaviour / rollback safety

Checked against the current code state and the latest accepted patch notes:

- `0_10_1`: one-button camera/live workflow and Manual Drive `r` / `s` shortcuts are preserved.
- `0_10_0`: v10 stable baseline behaviours remain intact.
- `0_9_10`: AI Mode recording/snapshot service integration, Start AI preview / drive controls, and AI update-loop work are preserved.
- `0_9_9`: TFLite runtime install guidance and diagnostics are preserved.
- `0_9_8`: keyboard steering release/focus handling is preserved.

This patch does not change motor steering math, AI inference, recording backend storage, overlay geometry, camera backend settings, runtime config schema, or safety gating.

## Verification actually performed

Applied locally on top of the current accepted `0.10.1` state, then ran:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All listed checks passed in this container.

## Not verified here

- Real Raspberry Pi browser rendering.
- Real Pi camera stream.
- Real keyboard shortcut input through Chromium.
- Real snapshot/recording file creation on the Pi.
- Real motor movement.

## Suggested Pi-side check after applying

1. Restart PiSD and hard-refresh the browser.
2. Confirm the front page Manual Drive and AI Mode cards are green.
3. Open Manual Drive and confirm the camera buttons read `Start live`, `Snapshot`, and `Record`.
4. Press `s` and confirm a snapshot is saved; press `r` and confirm recording toggles.
5. Open AI Mode and confirm the old `Refresh frame` button is gone.
6. Click `Start live` in AI Mode and confirm the live preview starts.
