# PATCH NOTES — CustomDrive_0_5_13

## Request summary
Patch the current CustomDrive Mission 1 line so that the Motor panel uses remembered **toggle boxes** instead of select dropdowns, and make sure the remembered setting affects **hardware motor output direction only**, not the Mission 1 software turn logic itself.

The user also explicitly asked that this remembered motor-output calibration continue to apply to the **start routing** section.

## Baseline / rollback review
This patch was built forward from the current accepted CustomDrive Mission 1 line represented in the workspace by:
- repo CustomDrive baseline
- accepted Mission 1 patches through `0_5_12`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_9.md`
- `PATCH_NOTES_CustomDrive_0_5_10.md`
- `PATCH_NOTES_CustomDrive_0_5_11.md`
- `PATCH_NOTES_CustomDrive_0_5_12.md`

Accepted behavior intentionally preserved:
- Mission 1 route -> camera -> model -> AI loop startup order
- current pickup / drop-off mission-state logic
- current Pi-side frame overlay and status reporting
- Arm Position panel and Motor Status panel
- current route executor and live turn helper
- remembered motor config persistence in the shared runtime config store
- start-route and live Mission 1 motion still use the same hardware-output calibration path

## Cause / root cause found
The current `0_5_12` Motor panel still exposed three direction controls:
- `left_direction`
- `right_direction`
- `steering_direction`

That created two problems relative to the user's updated requirement.

### 1. The UI control type was wrong
The current panel still used **select dropdowns** and a **Flip turn direction** button. The user explicitly wanted the motor direction calibration to be a **toggle box**.

### 2. The current Mission 1 panel still allowed changing `steering_direction`
`steering_direction` changes the Mission 1 software-side steering sign inside the shared `MotorService` mapping stage before left/right wheel outputs are produced.

That is not the same thing as calibrating the actual hardware motor output polarity.

The user explicitly asked that the remembered setting should affect:
- **hardware motor output setting only**

and should **not** affect:
- the Mission 1 software logic itself

So leaving `steering_direction` exposed in the Mission 1 Motor panel would continue to violate that requirement.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_13.md`

## Exact behavior changed

### 1. Mission 1 Motor panel now uses remembered toggle boxes for hardware motor output inversion
The Motor panel now shows one checkbox per wheel:
- **Left motor** → `Invert hardware output`
- **Right motor** → `Invert hardware output`

These are remembered settings and still save through the Mission 1 motor-config API.

### 2. Mission 1 no longer exposes `steering_direction` in the Motor panel
The Motor panel no longer shows:
- steering direction dropdown
- flip turn direction button

That means the Mission 1 page now calibrates **only** left/right hardware output polarity, which matches the user's requested behavior.

### 3. Mission 1 now forces software steering direction back to normal when applying motor defaults
`mission1_session_app.py` now pins:
- `steering_direction = 1`

when Mission 1 applies motor defaults at startup / session start.

This prevents an old previously saved `steering_direction` value from silently continuing to alter Mission 1 software turn logic.

### 4. Mission 1 hardware motor save path now persists left/right output direction and resets software steering direction to normal
When the Mission 1 Motor panel saves settings now:
- only `left_direction` and `right_direction` are taken from the web UI
- `steering_direction` is explicitly persisted as `1`
- the active `MotorService` is updated with:
  - remembered left/right output polarity
  - normal software steering direction

This keeps the remembered setting aligned with the user's requested rule:
- hardware output calibration is remembered
- software steering logic stays unchanged

### 5. Start-route motion still uses the same remembered hardware output calibration
Because the route executor still uses the shared Mission 1 `MotorService` path, the remembered left/right hardware-output direction toggles still affect:
- start-route turns
- start-route forward/backward output
- live pickup / drop-off motion

So the route section remains linked to the same hardware motor calibration, but now without exposing software steering-direction inversion in the Mission 1 UI.

### 6. Motor panel text now clearly states the rule
The Motor panel now explicitly tells the user:
- these toggle boxes change remembered **hardware motor output polarity** only
- Mission 1 turn logic and route logic stay the same

## Verification actually performed
The following checks were actually performed in the patched workspace:

1. Reconstructed the current CustomDrive Mission 1 workspace from the accessible repo baseline plus accepted Mission 1 patches through `0_5_12`.
2. Reviewed the recent patch-note history `0_5_9` through `0_5_12` before editing.
3. Inspected the current Mission 1 Motor panel code and confirmed it still used:
   - dropdown selectors
   - a steering-direction selector
   - a flip-turn button
4. Patched the backend so Mission 1:
   - applies left/right motor-output calibration as before
   - forces `steering_direction = 1` when applying defaults
   - saves only left/right hardware direction from the Mission 1 UI
   - persists `steering_direction = 1` to avoid stale software-logic inversion
5. Patched the frontend so the Motor panel now uses remembered checkbox toggles instead of selects.
6. Ran:
   - `python -m py_compile custom_drive/mission1_session_app.py`
   - `node --check custom_drive/mission1_web/static/app.js`
   - `python -m compileall custom_drive`
7. Checked the patch zip structure to ensure it is patch-only with the correct top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
1. This patch intentionally changes the Mission 1 Motor panel to calibrate hardware output polarity only.
   - if the user later wants a separate advanced control page for software steering inversion, that should be exposed separately and clearly labeled as software logic, not mixed into the same hardware toggle area

2. This patch does not add encoder feedback or physical wheel sensing.
   - the panel still reflects commanded motor output, not closed-loop measured wheel direction

3. The Mission 1 Motor panel still requires pressing the save button after changing the toggle boxes.
   - if desired later, the next forward patch can auto-save each checkbox change immediately
