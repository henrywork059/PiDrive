# AI Mode code map

This note is a maintainer map for the current AI Mode implementation. It is not a user workflow guide.

## Main backend files

- `pisd/services/ai_drive_service.py`  
  Live AI runtime coordinator. Keep this file focused on orchestration: model selection/loading, camera frame access, prediction loop, status payloads, and motor-service calls.

- `pisd/services/ai_correction.py`  
  Small deterministic helper module for AI correction settings and equations. This is the first place to check when debugging the Correction panel math. It can be tested without Flask, camera, AI model, or motors.

- `pisd/services/ai_safety.py`  
  Small deterministic helper module for the AI safety limiter. This is the first place to check when debugging max steering, max throttle, smoothing, or fixed-throttle behaviour.

- `pisd/app.py`  
  Flask route wiring. AI endpoints should stay thin and call the service layer rather than owning correction or safety math.

## Main frontend files

- `pisd/web/templates/ai_mode.html`  
  AI Mode page structure and panel IDs.

- `pisd/web/static/js/ai_mode.js`  
  AI Mode browser controller. It owns DOM updates, button wiring, shortcut wiring, model upload/delete calls, status refresh, Correction-panel input handling, and the Manual-pad takeover UI.

- `pisd/web/static/css/ai_mode.css`  
  AI Mode-specific layout and presentation.

- `pisd/web/static/js/overlay_geometry.js`  
  Shared overlay path geometry used by Manual Drive and AI Mode.

## Current correction path

```text
AI model output
  -> ai_correction.apply_additive_manual_correction()
  -> ai_safety.apply_ai_safety()
  -> MotorService.update()
```

Current equation:

```text
corrected = clamp(AI + manual * correction_gain, -1, 1)
correction_gain = Correction % / 100
```

Then the safety layer applies max steering, max throttle, smoothing, and fixed-throttle mode.


## Current manual takeover path

```text
AI Mode Manual pad
  -> /api/control/manual
  -> ai_drive_service.stop(..., stop_motors=False)
  -> MotorService.update()
```

The Manual pad is separate from Correction. It does not blend with AI output; it directly sends Manual Drive-style steering/throttle commands and should be treated as a takeover mode. Shared safety acknowledgement and motor-output enable controls remain outside the toggled panes so they are visible from Limiter, Correction, and Manual pad.

## Debugging checklist

When Correction behaviour looks wrong:

1. Check `/api/ai/status` fields: `last_raw_prediction`, `last_corrected_command`, `last_safe_command`, and `manual_correction`.
2. Confirm `last_corrected_command.equation` says `ai + manual * correction_gain`.
3. Confirm `manual_correction.active` is true while dragging or using arrow keys.
4. Confirm `last_safe_command.throttle` equals the fixed throttle when output mode is `AI steering + fixed throttle`.
5. Run `python3 scripts/test_ai_mode_page.py --static-only` for deterministic helper checks.

## Refactor boundary

Do not move hardware, camera, or motor calls into the helper modules. The helper modules should stay deterministic and side-effect free.
