# PiSD 0.5.9 Patch Notes

## Request summary
Improve the Manual Drive and AI Mode preview overlay presentation after online reference review. The overlay should no longer focus on a single car/arrow curve. It should show a road-style guide with two left/right path edges. Straight motion should appear as a perspective trapezium with the lower base at the bottom of the frame and the upper base near the horizon. Turning should bend the two road edges by different amounts. Reverse motion should not be drawn.

## Design logic used
- Road/track edges in camera perspective should converge toward a horizon/vanishing area when straight.
- Turning is represented as a corridor/road guide, where the inner and outer edges curve differently instead of one centre curve simply bending sideways.
- The centre arrow is kept only as a subtle direction cue; the two road edges are now the main visual guide.

## Files changed
- `pisd/__init__.py`
- `pisd/core/settings_manager.py`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/templates/ai_mode.html`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/static/css/ai_mode.css`
- `scripts/test_manual_drive_page.py`
- `scripts/test_ai_mode_page.py`
- `README.md`
- `docs/STABLE_BASELINE.md`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_5_9.md`

## Behaviour changed
- Manual Drive overlay now draws two curved road-edge guide lines.
- AI Mode overlay now uses the same road-edge guide style, driven by the safe AI command after the safety limiter.
- Straight forward motion forms a trapezium/perspective corridor.
- Turning bends the left and right road edges by different amounts.
- Reverse motion hides the road guide instead of drawing a reverse path.
- The previous car rectangle visual is hidden; the overlay no longer depends on a car-shaped marker.
- The default overlay line width is thinner and the road edges are more readable over the camera feed.
- Existing custom overlay calibration is preserved unless it matches known old defaults.

## Verification performed
- `python3 -m compileall pisd scripts`
- `python3 -m py_compile pisd/web/static/js/manual_drive.js` equivalent syntax check through Node when available
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_settings_persistence.py`

## Known limits / next steps
- The road guide is still a visual overlay only; it is not a calibrated camera-projection model.
- The exact horizon position may need real camera tuning after testing on the Pi car.
- Reverse motion is intentionally not drawn in this patch per request.
