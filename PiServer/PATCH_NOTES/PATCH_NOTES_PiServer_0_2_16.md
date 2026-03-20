# PiServer 0_2_16 Patch Notes

## Summary
This patch refactors the PiServer web workspace to reduce mixed panel responsibilities, make the top status area easier to read without scrolling, simplify manual controls, and improve tab-specific layouts.

## Main changes
- Combined the old status/telemetry content into one wide `Status / telemetry` panel.
- Reworked the status panel to prioritise the most important live values first, with more horizontal metric boxes and a clearer top-level summary.
- Replaced separate E-Stop/Clear controls with a single E-Stop toggle switch.
- Moved the preview backend/live text into an overlay at the bottom of the camera frame.
- Removed the old mixed `Drive + algorithm` panel and split responsibilities into:
  - `Runtime tuning`
  - `Model manager`
- Removed the old `System + config` panel from all tabs.
- Removed mode selection from runtime tuning.
- Removed the duplicate manual speed scale; max throttle is now the single speed-limit control used by manual inputs.
- Removed the old Forward/Reverse/Left/Right quick-drive buttons.
- Added stepped arrow-button/manual-key input:
  - press/hold ramps throttle/steering in `0.1` steps
  - release ramps back to zero at the same rate
- Added page-specific layout improvements across other tabs:
  - Manual: status, preview, runtime tuning, manual drive, recording
  - Training: status, preview, runtime tuning, model manager, recording
  - Auto: status, preview, runtime tuning, model manager
  - Camera: status, preview, camera settings
  - Motor: status, preview, motor settings

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`

## Notes
- This patch is UI-focused and does not change PiServer API routes.
- The E-Stop toggle colours follow the requested behaviour:
  - off = red
  - active = yellow
- The stepped return-to-zero behaviour applies to the manual arrow buttons and keyboard arrows/WASD.
