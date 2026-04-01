# PATCH NOTES — CustomDrive_0_4_15

## Request summary
Fix the Mission 1 web GUI because the panels appeared unclickable and the AI model panel did not respond when trying to load the selected model.

This patch is a forward bug-fix patch on top of the accepted `0_4_14` Mission 1 line.

## Requirements carried forward from the current Mission 1 line
This patch keeps the accepted Mission 1 behavior from the latest line, including:

- Mission 1 typed start route flow
- route -> camera -> model -> per-frame inference pipeline
- Pi-side annotated frame upload
- web detection table and overlay viewer
- model upload and selected-model workflow
- target object listing, FPS display, and Mission 1 status panels
- organised dashboard layout from `0_4_14`

No Mission 1 tracking, camera sequencing, or detection payload rules were intentionally changed in this patch.

## Cause / root cause
The Mission 1 control panels were not actually blocked by CSS layout or z-index.

The real root cause was a **JavaScript syntax error** in:

- `CustomDrive/custom_drive/mission1_web/static/app.js`

Inside `renderStatus()`, the recent mission-event lines were joined using a malformed multiline string literal:

- broken form in `0_4_14`: a literal line break was embedded inside `}).join(' ... ')`

That made the browser fail while parsing `app.js`.

Once the script failed during parse time:

- button click handlers were never attached
- refresh polling never started
- model list rendering never ran
- the AI panel looked visible but did nothing when clicked

So the panel issue was a script-load failure, not a backend model endpoint failure.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_15.md`

## Exact behavior changed

### 1. Fixed the Mission 1 web script parse error
The malformed multiline join in `renderStatus()` was corrected to a valid JavaScript newline join:

- now uses `}).join('\n');`

This allows the Mission 1 page script to load normally again.

### 2. Static asset version is bumped
The Mission 1 Flask app version string was updated to `0_4_15` so the browser requests the new JavaScript asset URL instead of reusing the broken cached `0_4_14` script.

### 3. Mission 1 panel click behavior is restored
Because `app.js` now loads correctly again, these controls are able to bind and respond:

- Save Mission 1 Config
- Start Mission 1
- Stop
- Set Selected Model
- Upload + Set Model

### 4. Model panel behavior is restored
The AI model panel can now:

- render the available uploaded model list
- submit the selected model to `/api/model/select`
- upload a `.tflite` file to `/api/models/upload`
- show success or error messages again

### 5. Mission 1 status polling is restored
Because the page script now initializes fully, Mission 1 web refresh behavior also resumes:

- `/api/status` polling
- status panel updates
- detection table updates
- summary card updates
- viewer note / overlay updates

## Verification actually performed
The following checks were actually performed:

1. Inspected the current `0_4_14` Mission 1 web files directly rather than guessing.
2. Reviewed the recent Mission 1 patch notes to avoid rollback risk:
   - `0_4_11`
   - `0_4_12`
   - `0_4_13`
   - `0_4_14`
3. Confirmed the actual root cause was a JavaScript syntax error in `app.js`, not a backend Flask route mismatch.
4. Compared the before/after file diff and kept the fix isolated to the single broken join statement.
5. Updated the Mission 1 app version string so the fixed static JavaScript is cache-busted as `?v=0_4_15`.
6. Ran:
   - `node --check CustomDrive/custom_drive/mission1_web/static/app.js`
   and the syntax check passed after the fix.
7. Ran:
   - `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py`
   and the Python file compiled successfully after the version bump.
8. Checked packaging so the patch zip contains only the changed Mission 1 file plus patch notes under the top-level `CustomDrive/` folder, with no `__pycache__` or `.pyc` files.

## Known limits / next steps
1. This patch restores the Mission 1 web script so the controls can respond again, but it does not change the backend model-loading pipeline itself.
2. If the page still appears unresponsive after applying this patch, the next thing to inspect on the Pi would be the browser developer console and Flask logs to see whether there is a second runtime error after script load.
3. This patch intentionally does not change viewer layout, detection overlay logic, route execution, or motor behavior.
4. If later requested, the next useful improvement would be to disable relevant buttons while requests are in flight and show a more explicit busy state in the Mission 1 model panel.
