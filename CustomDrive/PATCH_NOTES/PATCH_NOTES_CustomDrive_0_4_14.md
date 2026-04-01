# PATCH NOTES — CustomDrive_0_4_14

## Request summary
This patch is a forward Mission 1 web GUI patch with two direct goals:

1. **Organise the Mission 1 window layout** so the page is easier to use during testing.
2. **Make it draw a box around the objects** in the Mission 1 viewer.

This patch keeps the accepted `0_4_13` Mission 1 pipeline and does not change the route -> camera -> model -> per-frame inference flow that was rebuilt in that patch.

## Requirements carried forward from the current Mission 1 line
The Mission 1 behavior that remains in place after this patch is:

- the typed start route still runs first
- the camera still starts only after the route is finished
- the selected AI model is still loaded after the route and camera boot stages
- the Pi still runs per-frame inference and returns detection rows to the web UI
- the coordinate convention remains:
  - frame centre = `(0, 0)`
  - left = negative `x`
  - down = negative `y`
- the detected-object table still shows:
  - class ID
  - centre coordinates
  - box size
  - confidence
- Mission 1 target control still follows the current `0_4_13` target-`x` rule

## Cause / root cause
After the `0_4_13` pipeline rebuild, the Mission 1 page was functionally correct but still had two practical issues during use:

1. **The page layout was not organised enough for quick testing.**
   The controls, viewer, status, detections, and log areas all existed, but the overall arrangement still felt like a stack of separate panels rather than a mission dashboard.

2. **Object boxes were not explicit enough in the web viewer.**
   The backend already had Pi-side frame annotation code, but relying only on that made the visible boxes harder to confirm during debugging. The Mission 1 GUI also already had the detection coordinates, so the page could draw a second clear overlay around the objects directly in the browser using the uploaded box coordinates.

The correct forward fix was therefore:
- reorganise the Mission 1 dashboard layout
- keep Pi-side annotation
- add a browser-side overlay layer that draws boxes directly from the current detection list

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_14.md`

## Exact behavior changed

### 1. Mission 1 page layout was reorganised
The Mission 1 page is now structured as a clearer dashboard:

- **left sidebar**
  - Mission 1 setup
  - AI model controls
- **main upper area**
  - annotated viewer
  - quick summary cards
  - runtime status panel
- **bottom area**
  - detected objects table
  - mission trace/log panel

This makes the key runtime parts visible at the same time without mixing setup controls into the viewer area.

### 2. Viewer summary cards were added
The viewer section now shows compact Mission 1 summary cards for:

- phase
- object count
- target side
- car turn
- target X
- pipeline FPS
- camera FPS
- loaded model

These were added to make quick field testing easier without needing to read the full status panel.

### 3. Browser-side overlay boxes were added
The Mission 1 viewer now includes a dedicated SVG overlay layer on top of the frame.

The overlay uses the current detection rows returned by the Pi and draws:
- a rectangle around each detected object
- a label box with class ID, confidence, and centre coordinates
- a centre dot for each detection
- a highlighted style for the current target class

This means the viewer now shows boxes around objects even more explicitly, based on the same coordinates already uploaded to the web UI.

### 4. Deadband and frame axes are now shown in the viewer
The web overlay now also draws:
- the vertical centre line
- the horizontal centre line
- the current forward deadband region

This makes it easier to debug whether the target is inside the `|x| < 5%` forward region or outside it.

### 5. Pi-side box drawing was strengthened
The Mission 1 backend annotation path in `mission1_session_app.py` was also improved so the Pi-generated frame is easier to read:

- box outlines are now thicker
- target-class boxes are more prominent
- a center dot is drawn on each detection
- label backgrounds are drawn behind the class/confidence text

So this patch now gives **two aligned box-rendering paths**:
- Pi-side annotation on the JPEG frame
- web-side overlay boxes using the uploaded object coordinates

### 6. Existing Mission 1 pipeline behavior was preserved
This patch deliberately did **not** change:
- route parsing
- route execution order
- camera startup order
- model load order
- detection table payload shape
- centre-origin coordinate convention
- target-follow control rule from `0_4_13`

The goal was to improve the Mission 1 GUI and object visibility without rolling back the current session pipeline.

## Verification actually performed
The following checks were actually performed:

1. Reviewed the current Mission 1 line and recent patch-note history to avoid rolling back the accepted Mission 1 session pipeline.
2. Worked from the real `CustomDrive/` file paths and current Mission 1 web files.
3. Confirmed the patch stayed isolated to the Mission 1 session files only and did not touch:
   - older CustomDrive manual app
   - older generic CustomDrive web app
   - shared PiServer service files
4. Ran Python compile validation in a merged workspace that included:
   - the repo snapshot
   - the earlier Mission 1 added files
   - the current forward Mission 1 patch files
5. Checked the new viewer overlay logic against the existing Mission 1 detection payload fields so it uses the already-uploaded object coordinates and box dimensions.
6. Checked patch packaging so the zip contains only changed files plus patch notes under the top-level `CustomDrive/` folder, with no `__pycache__` or `.pyc` files.

## Known limits / next steps
1. This patch was checked at code level, but not with real Pi camera/video timing in this environment.
2. Because the viewer now uses both Pi-side annotation and browser-side overlay, any future mismatch between the two would indicate a coordinate scaling or aspect-ratio problem and should be debugged as a viewer-mapping issue rather than a detector-output issue.
3. The browser overlay currently refreshes by polling the Mission 1 status endpoint. If needed later, this can be moved to a streaming/event model.
4. If later testing shows that only one box-rendering path is needed, the project can choose between:
   - keeping both for debugging clarity
   - or simplifying to Pi-only or web-only overlay after validation.
