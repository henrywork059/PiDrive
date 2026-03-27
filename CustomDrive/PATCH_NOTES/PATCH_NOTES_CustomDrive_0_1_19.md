# PATCH NOTES — CustomDrive 0_1_19

## Request summary
Make a small forward-only GUI update:
- increase the **Arm Control** box height by about 50%
- give the **Arm Control** panel a different color so it stands out more clearly
- change **E-Stop** from two separate buttons into a real toggle switch

## Anti-rollback review performed
Reviewed the latest accepted GUI direction before patching:
- `0_1_18`: merged System into Status and stacked Arm Control vertically
- `0_1_17`: removed extra keyboard and direction-button drive inputs while keeping the drag pad
- `0_1_16`: established the current PiServer-style GUI layout, live camera, arm panel, drag pad, and separate settings overlays
- `0_1_15`: separated Drive Settings and Style Settings overlays

This patch keeps:
- the live camera panel
- the real PiServer motor drag-pad path
- the separate **Drive Settings** and **Style Settings** buttons
- the current arm actions and backend flow
- the merged **Status / System** panel direction from `0_1_18`

## Files changed
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_19.md`

## Exact behavior changed

### 1. Arm Control panel made taller and more distinct
The Arm Control panel now uses a larger default minimum height so it reads more like a dedicated control box instead of a narrow side card.

It also has a different color treatment:
- tinted panel background
- tinted panel header
- stronger arm button styling

This was done as a styling/layout update only. The arm control IDs and backend actions were kept the same.

### 2. E-Stop changed to a toggle switch
The old two-button flow:
- `E-Stop`
- `Clear E-Stop`

was replaced with one toggle switch control in the top **Status / System** panel.

Behavior now:
- switch **on** → sends `enabled: true` to `/api/system/estop`
- switch **off** → sends `enabled: false` to `/api/system/estop`

The toggle is also synced back from `/api/status`, so the UI reflects the real backend safety-stop state after polling.

### 3. Cache-busting version bumped
`gui_control_app.py` app version was bumped so the browser picks up the updated JS and CSS more reliably after replacing files on the Pi.

## Root cause / why this patch was needed
The arm panel was visually too similar to the other panels and did not stand out enough as a frequently used manual control area. The E-Stop flow also used two separate buttons instead of one clearer stateful control.

## Verification actually performed
- updated the latest GUI template, stylesheet, and JavaScript forward from the current GUI direction
- kept the existing arm button IDs and E-stop backend route intact
- ran `python -m compileall CustomDrive`

## Known limits / next steps
- this patch does not change camera logic, drag-pad logic, arm channel mapping, or backend safety-stop semantics
- if you want the arm panel even taller later, that should be tuned against your real browser/device resolution rather than hard-coding it much further
