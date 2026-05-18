# PATCH NOTES — PiSD_0_5_5

## Request summary

The requested change was to try reverse steering Option A first: when the car is moving backward, keep the steering value the same rather than automatically inverting it. The patch also needed to keep the AI Mode preview overlay aligned with the real command path.

## Root cause / reason for change

`MotorService.update(...)` already used the direct steering value for motor mixing, including reverse throttle. However, the Manual Drive and AI Mode predicted-path overlays visually inverted steering when throttle was negative. That made the overlay disagree with the command sent to the motor mixer.

## Files changed

- `pisd/__init__.py`
- `pisd/services/ai_drive_service.py`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/templates/ai_mode.html`
- `scripts/test_ai_drive_service.py`
- `scripts/test_ai_mode_page.py`
- `scripts/test_manual_drive_page.py`
- `docs/ERROR_CODES.md`
- `README.md`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_5_5.md`

## Behaviour changed

- Reverse steering Option A is now explicit:
  - positive steering remains positive even when throttle is negative;
  - negative steering remains negative even when throttle is negative;
  - no hidden reverse-steering inversion is applied by AI safety logic.
- Manual Drive predicted-path overlay now uses the same steering sign in reverse as the motor command.
- AI Mode predicted-path overlay now uses the same steering sign in reverse as the safe AI command.
- AI Mode status exposes `reverse_steering_policy: same_sign` in the safety layer.
- AI Mode page shows the current reverse steering policy as `same sign`.

## Compatibility notes

This patch does not add a user toggle yet. It intentionally tests Option A first. A future patch can add a persistent user setting if the real car feels more natural with inverted reverse steering.

## Verification actually performed

- `python3 -m compileall pisd scripts`
- `python3 scripts/test_ai_drive_service.py`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_manual_drive_page.py --static-only`

## Not verified

- Real Raspberry Pi motor direction on hardware.
- Real camera stream/browser overlay rendering.
- Full Flask route tests in this container.
