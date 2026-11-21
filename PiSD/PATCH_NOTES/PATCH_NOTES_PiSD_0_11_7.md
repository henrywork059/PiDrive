# PiSD 0.11.7 Patch Notes

## Request summary
- Fix AI Mode Snapshot so saving a snapshot does **not** freeze the live preview to the captured still frame.
- Reorder the AI output tabs to:
  1. Manual pad
  2. AI assist
  3. Correction
  4. Limiter
- Review and standardise the visible tab names as exactly:
  - Manual pad
  - AI assist
  - Correction
  - Limiter

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline with accepted patches `0_11_1` through `0_11_6` applied first.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_6.md`
  - `PATCH_NOTES_PiSD_0_11_5.md`
  - `PATCH_NOTES_PiSD_0_11_4.md`
  - `PATCH_NOTES_PiSD_0_11_3.md`
- Preserved the 0.11.6 three-rate FPS behavior: Camera capture FPS, Live preview FPS, and AI prediction FPS remain global settings.
- Preserved the 0.11.5 AI assist mode, last error log panel, and camera stop/start fix.
- Preserved the 0.11.4 global settings source and Manual speed default of 0.80.
- Preserved the 0.11.3 top-right safety confirmation placement.

## Cause / root cause
- The Snapshot button saved the recording frame, then called `setPreview('snapshot', /api/camera/frame.jpg...)`.
- That replaced the browser image source with a single still JPEG.
- If the live stream was running before Snapshot, the page visually froze because the preview image source was no longer `/video_feed`.
- The tab group also still showed the older order/title from the Limiter-first workflow after AI assist and Manual pad became more central to the current workflow.

## Files changed
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_7.md`

## Exact behavior changed

### Snapshot keeps live preview running
- AI Mode Snapshot still calls `/api/recording/capture` with `command_source: 'ai_safe_command'`.
- Snapshot no longer switches the preview image source to `/api/camera/frame.jpg`.
- If live preview is already active, the preview remains on `/video_feed` and continues updating.
- The caption now reports that the snapshot was saved while live stream was kept running.

### AI output tabs are reordered and renamed
- The panel title is now:

```text
Manual pad / AI assist / Correction / Limiter
```

- The tab order is now:

```text
Manual pad → AI assist → Correction → Limiter
```

- The visible tab labels are exactly:

```text
Manual pad
AI assist
Correction
Limiter
```

### Default visible tab
- The AI output panel now opens on **Manual pad** by default.
- This does not send motor commands by itself. Manual driving still requires the existing safety confirmation and user input.
- Existing Limiter, Correction, and AI assist behavior is preserved when those tabs are selected.

## Compatibility / migration notes
- No config schema change.
- No API change.
- No change to snapshot file format or recording labels.
- No change to the three-rate FPS settings.
- No change to AI assist steering formula.
- No change to motor safety confirmation behavior.

## Verification actually performed
Passed locally from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Results:
- Python compile check passed.
- AI Mode JavaScript syntax check passed.
- AI Mode static/source contract passed, including the new tab order check.
- Settings persistence test passed.
- Standard validation passed with API/camera/motor/GUI skipped.
- `PiSD.py --status-only` returned `PISD-OK-000` in simulation mode.

## Known limits / next steps
- Real Pi browser rendering and real live-stream snapshot behavior were not tested in this container.
- On the Pi, confirm this browser workflow:
  1. Start live.
  2. Click Snapshot.
  3. Confirm the preview keeps moving and does not freeze to the captured frame.
  4. Confirm the tab order is Manual pad, AI assist, Correction, Limiter.
