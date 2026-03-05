# PiCar Patch Notes — piCar_0_2_9

Date: 2026-03-05

## What you reported
1) **Status bar not showing all text** (especially on small screens / limited height).
2) **Manual Drag pad too big**.
3) **Buttons too large**.

## Root causes
- The **status panel** only spans **1 grid row**, so the title + padding consumes most of the height and the status line gets clipped.
- The **joystick area** was set to `width: 100%` so it always filled the panel.
- Button sizing was tuned for touch-first layouts; after increasing base font for readability, buttons became visually oversized.

## Fixes in this patch
### 1) Status bar always readable
- Removed the **"Status" title** in the status bar to reclaim vertical space.
- Forced status text to remain **one line** and enabled **horizontal swipe/scroll** inside the status bar:
  - `white-space: nowrap`
  - `overflow-x: auto; overflow-y: hidden`

Result: On small screens, you can always read the full status line by swiping horizontally.

### 2) Manual Drag pad reduced ~50%
- In the manual panel, the joystick box is now:
  - `width: 50%`
  - centered with `margin: 0 auto`
  - with safe limits: `min-width: 160px`, `max-width: 360px`

### 3) All buttons reduced ~20%
- Reduced button padding + font size in `ui_base.py`:
  - padding clamp values scaled down
  - font size reduced from `0.85rem` to `0.70rem`

## Files changed
- `ui_base.py`

## Verification steps (on Pi)
1) Restart the server:
   - `cd ~/piCar && python3 server.py`
2) Open the UI on:
   - phone (small screen)
   - tablet
   - PC browser
3) Confirm:
   - Status bar shows full info (swipe horizontally if needed)
   - Manual drag pad is ~half the previous size and centered
   - Buttons are visibly smaller (~20%) but still clickable

## Notes / next optional improvements
- If you want the status bar to **wrap into 2 lines** instead of horizontal scrolling, I can switch to `white-space: normal` and increase the status bar grid height (rowSpan) without breaking layout.
