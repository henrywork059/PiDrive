# PATCH NOTES — CustomDrive_0_5_11

## Request summary
Patch the current CustomDrive Mission 1 web GUI so that:

1. different Mission 1 stages are shown with clearer color coding
2. a new panel shows the live **arm position**
3. a new panel shows the live **motor status**
4. the motor panel uses color to show the **direction of rotation**

The user later clarified that the added arm and motor panels should be practical live-status panels, not new control surfaces.

## Baseline / rollback review
This patch was built forward from the current accepted CustomDrive Mission 1 line represented in the workspace by:
- uploaded `CustomDrive_0_5_0.zip` baseline
- accepted Mission 1 patches through `0_5_10`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_7.md`
- `PATCH_NOTES_CustomDrive_0_5_8.md`
- `PATCH_NOTES_CustomDrive_0_5_9.md`
- `PATCH_NOTES_CustomDrive_0_5_10.md`

Accepted behavior intentionally preserved:
- route -> camera -> model -> AI-loop startup order
- Mission 1 pickup / drop-off state machine
- stop-before-grip / stop-before-release state flow from `0_5_10`
- single-box viewer behavior from `0_5_9`
- live Pi-side frame overlay from `0_5_10`
- real `ArmService` backend and saved Mission 1 arm pose mapping
- current Mission 1 motor logic and calibrated motor-service path

## Cause / root cause found
The current Mission 1 line already exposed a lot of state information, but three practical UI gaps remained.

### 1. Stage coloring existed in the backend, but not strongly enough in the web UI
`mission1_session_app.py` already computed:
- `stage_theme`
- `motion_theme`
- `arm_theme`

Those were used on the Pi-side frame overlay, but the web GUI still looked mostly neutral. The user asked to color different stages more clearly, so the web UI needed to consume those theme payloads more visibly.

### 2. Arm position was only visible as text inside the generic status grid
The Mission 1 page already showed a short arm-angle line in the status grid, but there was no dedicated panel for:
- servo 0 / servo 1 / servo 2 angles
- channel numbers
- current moving / held state
- current arm stage / last loaded pose
- backend availability / hold-refresh state

So the web GUI technically had the data, but not in a usable live arm-status layout.

### 3. Motor outputs were only visible as raw numbers in the generic status grid
The Mission 1 page already showed:
- `last_command.left`
- `last_command.right`
- command note

But it did not show:
- left motor direction in a clean way
- right motor direction in a clean way
- whether the current command corresponds to clockwise / counterclockwise / forward / backward vehicle rotation
- color-coded motor direction at a glance

That made motor debugging harder than it needed to be.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_11.md`

## Exact behavior changed

### 1. Added a dedicated `motor_status` payload in the Mission 1 backend
The Mission 1 backend now publishes a more explicit motor-status block derived from the current Mission 1 command:
- left motor value
- right motor value
- left direction
- right direction
- power ratio per side
- interpreted vehicle rotation
- command mode / note

This is a status-only addition.
It does not change how the motors are commanded.

### 2. Stage / motion / arm themes are now used more clearly in the web GUI
The web UI now consumes the existing backend theme payloads more visibly in:
- summary cards
- status badges
- viewer stat pills
- arm-position panel
- motor-status panel

So the user can now see stronger color separation between:
- route / boot / pickup / tracking
- stop-for-pose / grip / lift / drop-off / release / reverse
- arm state vs motion state

### 3. Added a dedicated **Arm Position** panel
A new read-only panel now shows live arm backend status using the real `arm_status` payload.

It shows:
- current arm stage
- current pose number
- backend name
- sequence note
- backend enabled / available state
- hold-refresh running state
- speed multiplier
- live servo 0 angle and channel
- live servo 1 angle and channel
- live servo 2 angle and channel
- moving / held / disabled badges per servo

Each servo also gets a simple angle bar to make its live position easier to read.

### 4. Added a dedicated **Motor Status** panel
A new read-only panel now shows live motor output status using the current Mission 1 command.

It shows:
- current intended motion
- interpreted vehicle rotation
- GPIO availability
- left motor direction and output value
- right motor direction and output value
- a power bar per motor
- current command mode
- current command note

### 5. Added color-coded motor direction / rotation display
The motor panel now uses distinct color families for motor rotation state:
- **forward** → green
- **reverse** → red
- **clockwise** → yellow
- **counterclockwise** → purple
- **pivot** → blue
- **stopped** → grey

This is a web-status visualization only.
It does not change motor control logic.

### 6. Viewer stat pills now also show themed state / motion / arm badges
The viewer top stat area now keeps the neutral numeric pills for object count and FPS, but adds themed pills for:
- mission state
- intended motion
- arm stage

That makes the stage coloring visible near the live frame as well as in the lower panels.

## Verification actually performed
The following checks were actually run:

1. Reconstructed the current CustomDrive Mission 1 workspace from the available baseline plus accepted Mission 1 patch line through `0_5_10`.
2. Reviewed the recent Mission 1 patch notes `0_5_7` through `0_5_10` before editing.
3. Inspected the real current Mission 1 status payload and confirmed:
   - stage/motion/arm theme payloads already existed in the backend
   - arm state was only exposed through the generic status grid
   - motor output state was only exposed through raw command values in the generic status grid
4. Patched the backend to add an explicit `motor_status` payload without changing the control path.
5. Patched the Mission 1 web template / JS / CSS to add:
   - a new Arm Position panel
   - a new Motor Status panel
   - stronger stage / motion / arm color usage
   - color-coded motor rotation display
6. Ran:
   - `python -m py_compile custom_drive/mission1_session_app.py`
   - `node --check custom_drive/mission1_web/static/app.js`
   - `python -m compileall custom_drive`
7. Checked the patch zip structure to ensure it is patch-only with the correct top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
1. The new motor panel shows the interpreted command-level rotation state from the Mission 1 command that was sent.
   - it does not add encoder feedback or true wheel-speed sensing
   - so it is still a control-status view, not physical closed-loop confirmation

2. The arm panel shows the live angles that the current `ArmService` believes it is holding.
   - it does not add external position sensing
   - so it is still a backend-status view, not absolute mechanical verification

3. This patch improves color readability in the web GUI but does not redesign the page layout structure.
   - if desired later, the next UI patch could collapse the status grid and move more items into dedicated cards

4. This patch intentionally does not change Mission 1 motion decisions, arm sequencing, detector flow, or route execution.
   - it is a forward observability / usability patch only
