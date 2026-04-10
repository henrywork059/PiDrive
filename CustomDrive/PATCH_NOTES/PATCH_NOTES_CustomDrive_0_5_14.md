# PATCH NOTES — CustomDrive_0_5_14

## Request summary
Patch the current CustomDrive Mission 1 line so that:

1. the Motor panel no longer uses self-resetting checkbox controls
2. the Motor panel uses remembered **toggle box buttons** instead
3. the Mission 1 Motor panel adds back a separate **turn logic** control so the user can choose:
   - **normal**: turn left = left motor backward, right motor forward
   - **inverted**: turn left = left motor forward, right motor backward
4. the remembered hardware motor direction controls continue to affect **hardware motor output calibration**
5. the remembered turn-logic control affects the **software turn mapping** used by Mission 1 and the start route
6. arm status is clearer in a non-Pi / logic-test environment where no real arm hardware backend is present

The user explicitly clarified that they are currently **not testing on the Pi**, so the patch also needed to make the arm status behave more truthfully in a logic-only environment.

## Baseline / rollback review
This patch was built forward from the current accepted CustomDrive Mission 1 line represented in the workspace by:
- repo CustomDrive baseline
- accepted Mission 1 patches through `0_5_13`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_10.md`
- `PATCH_NOTES_CustomDrive_0_5_11.md`
- `PATCH_NOTES_CustomDrive_0_5_12.md`
- `PATCH_NOTES_CustomDrive_0_5_13.md`

Accepted behavior intentionally preserved:
- current Mission 1 route -> camera -> model -> AI loop startup order
- pickup / drop-off mission state machine and pose timing
- Arm Position panel and Motor Status panel
- live Pi-frame mission overlay and web status flow
- remembered hardware motor calibration support
- current route executor linkage to shared motor calibration
- current Mission 1 motor-service based live turning path

## Cause / root cause found
There were three connected issues in the current Mission 1 line.

### 1. The Motor panel controls were the wrong UI shape for a live polled page
In `0_5_13`, the Motor panel switched to checkbox inputs for left/right hardware direction.

However, the Mission 1 page re-renders the whole Motor panel on each status refresh.
That means an unsaved checkbox state can appear to "uncheck itself" as soon as the next poll redraws the panel from backend state.

So even if the backend logic was correct, the UI control model was wrong for a fast-polled live page.

### 2. The earlier software turn-logic control had been removed entirely
`0_5_13` intentionally removed the Mission 1 steering-direction UI and forced `steering_direction = 1` in the Mission 1 motor-default path.

That matched the earlier requirement at the time, but the user now explicitly wants the software turn mapping back as a separate control.

So the current code no longer matched the latest explicit user instruction.

### 3. In a non-Pi logic test environment, arm status looked like repeated hardware failure instead of simulation
The pasted runtime log showed repeated warnings like:
- `No module named 'adafruit_servokit'`

But the same log also showed the Mission 1 arm logic continuing through:
- grip ready
- grip
- grip and lift
- held class update

That means the logic path was working, but the backend had no hardware library.

So the current arm status behavior was technically truthful about missing hardware, but not useful for the user's stated workflow of logic-only testing.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_14.md`

## Exact behavior changed

### 1. Left/right motor direction controls now use remembered toggle box buttons
The Motor panel no longer uses checkbox inputs.

It now shows clickable toggle box buttons for:
- left hardware output
- right hardware output

Each button now displays its current remembered state:
- `Normal`
- `Inverted`

Each click immediately saves the new backend value instead of waiting for a separate save button.

This fixes the self-resetting UI problem caused by live panel re-renders.

### 2. Turn logic control was added back as a separate remembered toggle box button
The Motor panel now also includes a distinct **Turn logic** toggle box button.

States:
- `Normal`
- `Inverted`

Meaning:
- **normal**:
  - turn left = left motor backward, right motor forward
- **inverted**:
  - turn left = left motor forward, right motor backward

This is stored through `steering_direction` again and is intentionally separate from hardware output polarity.

### 3. Hardware output calibration and software turn logic are now clearly separated again
The backend save path now distinguishes:
- `left_direction`
- `right_direction`
- `steering_direction`

Rules after this patch:
- **left/right hardware output buttons** affect only the remembered motor-output polarity
- **Turn logic button** affects the Mission 1 software turn mapping

That means the user now has both:
- wheel-output calibration
- turn-logic inversion

without mixing them into one control.

### 4. Mission 1 motor defaults no longer forcibly reset steering logic to normal
`mission1_session_app.py` no longer forces `steering_direction = 1` inside `_apply_motor_defaults()`.

Instead, it applies the real saved motor config so that:
- the new turn-logic button is actually respected
- both the start route and live Mission 1 turning use the same remembered software turn mapping

### 5. Start-route motion remains linked to the same motor logic
Because the Mission 1 start route still runs through the shared calibrated motor path, the following now all use the same remembered settings:
- left hardware output inversion
- right hardware output inversion
- normal/inverted software turn logic

So the user-requested turn logic is now linked to:
- Mission 1 live turning
- start routing section

### 6. Non-Pi arm backend now falls back to simulation mode when `adafruit_servokit` is missing
`arm_service.py` now detects the specific missing-library case:
- `ModuleNotFoundError: adafruit_servokit`

In that case it now enters:
- `backend = simulated`
- `simulated = True`
- `hardware_available = False`
- `available = True`

This allows:
- arm pose logic to keep running
- current servo angles to update in software
- Mission 1 posture sequencing to be tested without hardware

No physical servo output is sent in this mode.

### 7. Arm status UI now explicitly shows simulation state
The Arm Position panel now shows:
- backend mode
- whether the backend is simulated
- whether hardware is available

It also changes the status badges and footer note so the user can immediately tell the difference between:
- real hardware mode
- simulation / logic-only mode

### 8. Manual pose loads in a non-Pi environment now behave like logic-only arm updates instead of repeated backend failures
Because the simulated backend now accepts pose application in software, Mission 1 logic testing no longer has to rely on repeated warning-only behavior when no real Pi arm backend exists.

## Verification actually performed
The following checks were actually performed in the patched workspace:

1. Reconstructed the current CustomDrive Mission 1 workspace from the accessible repo baseline plus accepted Mission 1 patches through `0_5_13`.
2. Reviewed recent patch-note history `0_5_10` through `0_5_13` before editing.
3. Inspected the current Mission 1 Motor panel code and confirmed:
   - it still used checkbox inputs
   - it still had no separate turn-logic control
   - its live re-render pattern could make unsaved checkbox state appear to reset
4. Inspected the current Mission 1 backend motor save path and confirmed it still forced `steering_direction = 1`.
5. Inspected the current arm service and confirmed that missing `adafruit_servokit` left the backend unavailable rather than simulated.
6. Patched the backend so Mission 1 motor calibration now saves and applies:
   - `left_direction`
   - `right_direction`
   - `steering_direction`
7. Patched the frontend so the Motor panel now uses immediate-save toggle box buttons instead of checkboxes.
8. Patched the arm service so the specific missing-driver case enters simulation mode for logic testing.
9. Ran:
   - `node --check custom_drive/mission1_web/static/app.js`
   - `python -m py_compile custom_drive/mission1_session_app.py custom_drive/arm_service.py`
   - `python -m compileall custom_drive`
10. Checked the patch zip structure to ensure it is patch-only with the correct top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
1. The simulated arm backend is intended for logic testing when the Pi arm driver library is not present.
   - it updates pose state in software only
   - it does not verify real servo motion

2. This patch does not add a dedicated advanced calibration page.
   - the controls are still in the Mission 1 Motor panel

3. This patch does not add a separate restore-defaults button for motor calibration.
   - if needed later, the next forward patch can add a one-click reset to:
     - left output normal
     - right output normal
     - turn logic normal

4. The current Motor panel still reflects commanded outputs, not encoder-measured real wheel motion.
