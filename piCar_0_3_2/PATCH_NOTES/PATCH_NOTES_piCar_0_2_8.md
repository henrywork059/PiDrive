# PiCar Patch Notes — piCar_0_2_8

Date: 2026-03-05

## Issue
On smaller screens (phones / small browser windows), the Web UI text became **too small to read**.

## Root Cause
The responsive typography was driven by `vmin` with a low minimum (`--font-base: clamp(12px, 1.35vmin, 18px)`), which allowed the base font size to settle at **12px** on small devices.

Some mobile browsers may also try to automatically adjust/shrink text inside constrained layouts unless `text-size-adjust` is explicitly set.

## Attempted Fixes
- Verified that OpenCV/Flask rendering and panel scroll behavior were not affecting font rendering.
- Confirmed the issue was purely CSS sizing on small viewports.

## Final Fix
Updated `ui_base.py` to make typography **more readable on small screens**:

1) Increased the minimum base font size:
- `--font-base` now uses a **higher minimum (14px)**.

2) Added a small-screen media query:
- For screens `<= 520px`, `--font-base` is bumped to **16–18px** using `clamp(16px, 4.2vw, 18px)`.

3) Prevented unwanted mobile text shrinking:
- Added `-webkit-text-size-adjust: 100%` and `text-size-adjust: 100%` to `body`.

## Files Changed
- `ui_base.py`

## Verification Steps
1) Start the server:
   - `python3 server.py`
2) Open the UI on:
   - Phone (portrait + landscape)
   - Tablet
   - Desktop browser window resized small
3) Confirm:
   - Text remains readable on small screens
   - Buttons still scale nicely
   - Panel internal scrolling still works when content overflows

## Notes / Future Improvements
- If you want **sticky panel titles** (header stays visible while the panel content scrolls), we can add:
  - `position: sticky; top: 0;` to `.panel-title` with a subtle background.
