# PiServer 0_2_11 Patch Notes

## Summary
This patch tightens the PiServer web workspace, improves the default dock layout, and makes the status panel hold up better when the available width is reduced.

This was applied directly on top of the current PiDrive repo snapshot provided in this chat. The patch only updates the PiServer frontend/runtime version markers and does **not** roll back unrelated work.

## Problems addressed

### 1) Status panel could feel cut off in tighter layouts
The status panel was using a compact two-row default height while still trying to show:
- 6 metric cards
- the live banner message

When the window width got tighter, the metric cards wrapped more aggressively and the panel could feel like not all boxes were visible without extra scrolling.

### 2) Default layout still wasted space
The default page layouts were functional, but they still left avoidable dead space around the status strip and bottom-row utility panels.

### 3) UI spacing still felt too loose
Buttons, panel padding, gaps, badges, and helper text were still slightly roomy for a dense dashboard-style control surface.

## Changes made

### A) Better default layouts
Updated the built-in default panel layouts for:
- manual
- training
- auto
- camera
- motor

Main layout adjustments:
- increased the default **status** panel height from 2 rows to 3 rows
- shifted the main viewer and right-side control panels down to match the taller status area
- tightened the lower record/system panel arrangement
- kept the overall workspace within the same 24x14 dock grid

### B) Status panel made more compact and resilient
Refined the status panel styling so it handles narrower widths better:
- reduced metric card minimum width
- reduced metric card padding
- reduced label and value font size slightly
- reduced banner spacing
- made the status panel body a tighter vertical flex stack
- added an extra narrower-width breakpoint for the metric card sizing

This gives the status panel more room to keep all metrics visible before wrapping becomes a problem.

### C) Reduced spacing and margins further across the UI
Tightened the workspace visually by reducing:
- global panel gap
- corner radius slightly
- grid row height slightly
- top bar padding
- workspace shell padding
- panel header/body padding
- button/select/file input padding and minimum height
- field spacing
- banner padding
- checkbox row padding
- quick-drive button basis
- resize handle footprint
- badge sizing

### D) Forced a fresh saved-layout namespace
Updated the layout storage key version so the browser picks up the new built-in layouts automatically instead of staying stuck on older saved localStorage positions.

### E) Updated app version marker
Updated the PiServer frontend cache-busting version from `0_2_10` to `0_2_11`.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_11.md`

## Verification performed
The following checks were actually run:

1. Python syntax compilation:
   - `python -m compileall PiServer`

2. JavaScript syntax check:
   - `node --check PiServer/piserver/web/static/app.js`

## Notes
- Existing user-saved runtime configuration files were not reset.
- The patch only changes PiServer frontend/runtime presentation behavior and version markers.
- Existing unrelated project code in the repo was left untouched.

## Possible future follow-up
If needed, the next refinement could add:
- per-panel compact modes
- snap/merge-aware smarter default layouts by page type
- optional hidden/collapsed status banner when space is extremely tight
