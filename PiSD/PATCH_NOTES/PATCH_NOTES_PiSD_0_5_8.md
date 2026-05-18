# PiSD 0.5.8 Patch Notes — Curvier Thin Arrow Overlay Refinement

## Request summary
- Make the Manual Drive / AI Mode overlay curve more visibly curly.
- Make the default overlay line thinner.
- Improve the presentation of the arrowed curve.
- Re-check online design logic and apply it to the overlay implementation.

## Design logic applied
- Kept the overlay as a visual predicted-path guide only; motor output, Manual Drive command logic, AI safe command logic, and reverse same-sign steering policy are unchanged.
- Retained the car-like curvature idea: steering controls path curvature and throttle controls visible path length.
- Tuned the visual model for a small live camera frame:
  - shorter visual wheelbase for a tighter screen curve,
  - nonlinear steering response so small steering values are easier to read,
  - bounded steering angle and bounded turn sweep so the path does not curl into unreadable off-screen loops,
  - horizontal fit-to-frame scaling so high-curvature paths stay inside the overlay area.
- Improved the SVG arrow marker presentation:
  - larger arrow marker,
  - cleaner arrow geometry,
  - light stroke around the arrow head,
  - non-scaling strokes for the guide/path layers.

## Files changed
- `pisd/__init__.py`
  - Version bumped to `0.5.8`.
- `README.md`
  - Updated current patch line and overlay summary.
- `pisd/core/settings_manager.py`
  - Updated default Manual Drive overlay calibration values.
  - Added safe migration from the 0.5.7 uncustomised overlay defaults to the 0.5.8 defaults.
  - Expanded the curve-strength clamp to allow stronger visual curvature.
  - Lowered the minimum path-width clamp to allow a thinner line.
- `pisd/web/static/js/manual_drive.js`
  - Increased default curve strength to `1.95`.
  - Reduced default path width scale to `0.55`.
  - Added bounded visual curvature logic and fit-to-frame path scaling.
  - Reduced dynamic stroke widths.
- `pisd/web/static/js/ai_mode.js`
  - Applied the same bounded curvier/thinner overlay model to AI Mode.
- `pisd/web/templates/manual_drive.html`
  - Updated arrow marker shape and size.
  - Updated overlay calibration control defaults.
  - Updated overlay calibration note.
- `pisd/web/templates/ai_mode.html`
  - Updated AI overlay arrow marker shape and size.
- `pisd/web/static/css/manual_drive.css`
  - Thinned default path/guide/halo styling.
  - Improved arrowhead outline and glow.
  - Added non-scaling stroke behavior for SVG overlay paths.
- `pisd/web/static/css/ai_mode.css`
  - Updated AI overlay comments and matching line colours.
- `scripts/test_settings_persistence.py`
  - Updated expected overlay default opacity for 0.5.8.

## Behaviour changed
- Manual Drive overlay appears more curved for the same steering value.
- AI Mode overlay appears more curved for the same AI safe steering value.
- Default path line is thinner and less blocky.
- Arrowhead is clearer and easier to see on live camera video.
- Very tight curves are bounded/fitted so the arrow path stays visible inside the preview overlay.

## Compatibility notes
- Existing user-customised overlay settings are preserved.
- Only known unmodified defaults from the old overlay settings are migrated.
- Motor control is unchanged.
- AI safety limiting is unchanged.
- Reverse steering Option A remains unchanged: negative throttle keeps the same steering sign.

## Verification actually performed
- `python3 -m compileall pisd scripts PiSD.py` passed.
- `node --check pisd/web/static/js/manual_drive.js` passed.
- `node --check pisd/web/static/js/ai_mode.js` passed.
- `python3 scripts/test_manual_drive_page.py --static-only` passed.
- `python3 scripts/test_ai_mode_page.py --static-only` passed.
- `python3 scripts/test_settings_persistence.py` passed.
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui` passed.

## Known limits / next steps
- Final visual quality still needs checking on the real Pi camera feed.
- The overlay is still an approximate screen guide, not a precise physical simulator.
- If it is still not curly enough on the real car, increase the Manual Drive overlay calibration `Curve strength` slider before changing motor behaviour.
