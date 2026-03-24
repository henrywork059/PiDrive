# PATCH NOTES — CustomDrive 0_1_18

## Request summary
Make a small forward-only GUI update:
- merge the **System** panel into the **Status** bar/panel
- arrange **Arm Control** buttons vertically
- increase arm button height

## Anti-rollback review performed
Reviewed the latest accepted CustomDrive GUI direction before patching:
- `0_1_17`: removed extra keyboard and direction-button drive inputs while keeping the drag pad
- `0_1_16`: established the current PiServer-style GUI layout, live camera, arm panel, drag pad, and separate settings overlays
- `0_1_15`: separated Drive Settings and Style Settings overlays

This patch keeps:
- the live camera panel
- the drag pad and real PiServer motor control path
- the separate Drive Settings and Style Settings buttons
- the current arm control actions and settings flow

## Files changed
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_18.md`

## Exact behavior changed

### 1. System and Status merged
The separate **System** panel was removed from the workspace and its content was merged into the full-width **Status / System** panel at the top.

The merged panel now contains:
- existing status metrics
- runtime path
- arm lift readout
- motor direction readout
- preview / E-stop / clear E-stop buttons
- status banner
- system banner

### 2. Layout simplified
The main workspace grid now uses:
- top full-width merged status/system panel
- left arm panel
- center camera viewer
- right manual drive panel

This reduces panel sprawl and gives more room to the main control panels.

### 3. Arm buttons restacked vertically
The arm button group changed from a 2x2 grid to a single vertical column.

### 4. Arm buttons made taller
Arm buttons now use a larger minimum height so they are easier to press on touch devices and in the browser.

## Root cause / why this patch was needed
The separate System panel used extra space for a small set of controls and readouts, while the arm buttons were tighter than needed for repeated manual use. Merging the status/system content and simplifying the arm button stack makes the page easier to use without changing the existing control logic.

## Verification actually performed
- updated the latest GUI template and stylesheet only
- checked that existing JavaScript IDs remain present after the merge
- ran `python -m compileall CustomDrive`

## Known limits / next steps
- this patch does not change camera logic, drag pad logic, or backend control paths
- if needed later, the merged top panel can be made denser or more compact without reopening the full layout direction
