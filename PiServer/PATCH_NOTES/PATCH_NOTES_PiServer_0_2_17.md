# PiServer 0_2_17 Patch Notes

## Summary
This patch refactors the PiServer web UI layout and manual-control behavior to make the dashboard easier to read, easier to dock, and more stable during live use.

## Main changes
- Combined **Status** and **Telemetry** into one wide horizontal **Status / Telemetry** panel.
- Moved **E-Stop** into its own dedicated panel and changed it to a single toggle-style control.
- Reduced the visual docking grid size by using a finer layout grid with smaller gaps and shorter default rows.
- Reworked panel sizes and default tab layouts so important information is visible earlier with less scrolling.
- Improved panel content responsiveness so metric cards, form fields, and manual controls wrap and resize more gracefully as the panel size changes.
- Removed the old **System + config** panel.
- Removed runtime **mode/algorithm selection** from the runtime tuning area.
- Kept **Max throttle** as the single speed scaling control and removed the duplicate manual speed slider.
- Removed the old forward / reverse / left / right quick-drive buttons.
- Added a smoother stepped manual control pad using **↑ ← • → ↓** with hold-to-ramp and release-to-center behavior.
- Fixed joystick drag behavior so holding the mouse in one place no longer drifts back to zero until release.
- Moved camera preview backend/live text into a bottom overlay on the frame.
- Updated the Manual, Training, Auto, Camera, and Motor tab layouts to use cleaner panel combinations.

## Manual control behavior changes
- Keyboard and pad input now step target values by **0.1** at a fixed interval instead of snapping straight to full output.
- When the user releases the key or pad button, steering and throttle ramp back toward zero at the same step rate.
- The live output also eases toward the target each tick to make the control feel smoother.
- Pointer drag on the joystick now keeps the target steady while the pointer is held still, and only returns to zero after release.

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/app.py`

## Notes
- This patch is UI-focused and does not overwrite `config/runtime.json`.
- A browser hard refresh is recommended after updating because the web asset version was bumped to `0_2_17`.
