# PiSD_0_4_9 Patch Notes

## Request summary

Implement the planned `PiSD_0_4_9` patch for Manual Drive preview FPS / latency and camera-state reliability.

The requested focus was:

- improve the Manual Drive live camera preview pipeline;
- avoid unnecessary preview reloads and duplicate preview loops;
- separate camera service running state from browser preview mode;
- add stale-frame / no-new-frame visibility;
- keep Refresh status non-invasive;
- keep the 0_4_5 to 0_4_8 Manual Drive overlay, calibration, and safety behavior intact.

## Baseline / anti-rollback check

This is a cumulative patch built forward from `PiSD_0_4_0` and preserves the effective changes from `0_4_1` through `0_4_8`.

Checked against the previous Manual Drive patch line before finalising:

- `0_4_5`: Manual Drive overlay toggle remains on the Manual Drive page.
- `0_4_6`: sampled predicted-arc overlay remains in use.
- `0_4_7`: overlay calibration and live source/debug panel remain in use.
- `0_4_8`: STOP behavior, one command-state path, Refresh status separation, and page-leave fail-safe stop remain in use.

## Cause / root cause

The Manual Drive preview image still loaded `/api/camera/frame.jpg` directly when the page opened. In PiSD, that endpoint can start the camera if no cached frame exists. This could blur the meaning of the Start camera / Live stream buttons because the preview path might touch the camera before the user explicitly asked for it.

The page also did not have a single guarded preview metrics loop. Without explicit preview state, it was harder to see the difference between:

- camera service running;
- browser preview idle;
- snapshot preview selected;
- MJPEG live preview selected;
- stale/no-new-frame condition.

## Files changed / included

This cumulative patch zip includes the prior changed files and notes from `0_4_1` through `0_4_8`, plus these `0_4_9` updates:

- `PiSD/pisd/__init__.py`
  - Bumped version to `0.4.9` for static asset cache-busting.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Manual Drive preview now starts with an idle placeholder instead of immediately requesting `/api/camera/frame.jpg`.
  - Added preview debug fields:
    - Preview mode;
    - Camera running;
    - Frame age;
    - Preview FPS;
    - Live loop.
  - Updated the help text so Start camera / Live stream / Refresh status meanings are clearer.
- `PiSD/pisd/web/static/js/manual_drive.js`
  - Added a guarded preview metrics loop using `/api/camera/fps-stats`.
  - Added explicit preview modes: `idle`, `snapshot`, and `live`.
  - Added preview states: `idle`, `loading`, `active`, `stale`, `camera-off`, and `error`.
  - Added stale-frame detection based on the camera `last_frame_at` timestamp.
  - Added FPS estimation from frame sequence deltas when available, falling back to backend measured FPS when needed.
  - Ensured only one preview metrics loop runs at a time.
  - Stopped the preview metrics loop on hidden/page-unload paths while preserving the existing motor fail-safe stop.
  - Kept overlay redraw tied to command/settings changes instead of camera-frame refresh.
- `PiSD/pisd/web/static/css/manual_drive.css`
  - Added visible preview-state styling for loading/stale/error states.
  - Added subtle outline differences for snapshot and live modes.
  - Expanded the debug panel layout so the new preview debug fields fit better.
- `PiSD/scripts/test_manual_drive_page.py`
  - Extended Manual Drive static checks for preview idle state, guarded metrics loop, FPS/stale debug fields, and no auto-preview-start contract.
- `PiSD/scripts/run_standard_validation.py`
  - Extended the standard static source contract for the new preview reliability tokens.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_9.md`
  - Added these notes.

## Exact behavior changed

### 1. Manual Drive preview starts idle

The Manual Drive page no longer requests `/api/camera/frame.jpg` immediately on page load.

Instead, the preview frame shows an idle placeholder until the user chooses:

- `Start camera` for snapshot preview;
- `Live stream` for MJPEG preview.

This makes the button meanings cleaner and avoids accidental camera-path activation during page load.

### 2. Start camera / Live stream are clearer

- `Start camera` posts `/api/camera/start`, then refreshes a snapshot frame.
- `Live stream` posts `/api/camera/start`, then switches the image to `/video_feed`.
- `Refresh status` still only calls status/file-list refresh paths and does not start/restart camera preview or send motor commands.

### 3. Preview health/debug fields added

The status/debug area now shows:

- Preview mode: `idle`, `snapshot`, or `live`;
- Camera running: yes/no/unknown;
- Frame age;
- Preview FPS;
- Live loop: on/off.

These are intended to help identify whether lag comes from backend capture, browser preview mode, or stale frames.

### 4. Stale-frame warning

If the preview is in live mode and the camera reports no fresh frame for more than the local stale threshold, the preview frame is marked stale and a short warning is shown.

### 5. Duplicate loop prevention

The preview metrics loop is guarded. Repeated clicks on Live stream or Start camera will not create multiple JS intervals for the same FPS/stale checks.

## Compatibility notes

- No backend route was renamed or removed.
- Motor command behavior is not changed.
- Overlay path geometry and calibration settings are not changed.
- Runtime settings are not reset.
- `/api/camera/frame.jpg` remains available for snapshot refresh, but Manual Drive no longer loads it automatically at initial page render.

## Verification actually performed

Performed locally after applying this cumulative patch over a clean `PiSD_0_4_0` folder:

```bash
python3 -m compileall -q .
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-gui --skip-api --skip-camera --skip-motor
```

All listed checks passed.

## Known limits / next steps

- Hardware camera and real browser MJPEG behavior were not tested in this container.
- Full Flask route/API validation was skipped here because this environment is not the Pi runtime environment.
- Browser `<img>` elements do not reliably expose every MJPEG frame event, so the preview FPS estimate is based mainly on backend frame sequence / FPS stats rather than direct per-frame browser decode timing.
- A future patch could add a backend manual-command watchdog so the Pi automatically stops motors if no fresh command arrives within a short timeout.

## Apply

From the PiDrive parent folder:

```bash
cd ~/PiDrive
unzip -o PiSD_0_4_9_patch.zip
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then hard refresh the browser with `Ctrl + F5` so the `v=0.4.9` static assets are loaded.
