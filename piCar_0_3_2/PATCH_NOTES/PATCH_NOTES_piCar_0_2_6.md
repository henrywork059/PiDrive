# PiCar Patch Notes — piCar_0_2_6

Date: 2026-03-05

## Goal
Make the **Web GUI button + text sizes automatically scale** to different device screen sizes (phone / tablet / laptop) without needing manual zoom.

## Root cause
The Web UI CSS in `ui_base.py` used mostly fixed pixel values (`gap: 8px`, `padding: 10px 12px`, joystick dot `18px`, etc.) and many `em` sizes. On small screens, these elements can look cramped or too small; on large screens, they can look overly large or “lost”.

## What I changed
**File changed:** `ui_base.py`

### 1) Added responsive CSS variables (using `clamp()` + `vmin`)
In `:root` I added:
- `--font-base: clamp(12px, 1.35vmin, 18px)`
- `--pad-panel-x / --pad-panel-y`
- `--gap`, `--pad-layout`, `--radius`

These values scale with the **smaller viewport dimension** (`vmin`) and stay within sensible minimum/maximum sizes (`clamp`).

### 2) Made text scale from a single base
- Set `body { font-size: var(--font-base); line-height: 1.25; }`
- Converted several UI text sizes from `em` to `rem` so they scale consistently with the base.

### 3) Made touch targets scale (buttons + indicators)
- Buttons: padding uses `clamp(...)` so they remain finger-friendly on phones.
- Joystick dot and record status dot sizes scale with the screen.

## How to verify
1) Start server on Pi:
   ```bash
   cd ~/piCar
   python3 server.py
   ```
2) Open the UI on:
   - Phone browser
   - Tablet browser
   - Desktop browser
3) Confirm:
   - Titles and text are readable without zooming
   - Buttons have comfortable tap size on phone
   - Layout spacing/padding feels proportional across devices

## Notes / future improvements
- If you later want the **layout to switch to a stacked/mobile layout** (instead of the current 30x20 grid), we can add a mobile breakpoint like `@media (max-width: 900px)` to rearrange panels into a vertical flow.
