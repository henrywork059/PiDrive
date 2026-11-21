# PATCH NOTES — CustomDrive_0_5_17

## Request summary
Implement **U24** and the closely related visual refinement from the PiDrive roadmaps: show separate, labeled pickup/grip and drop-off threshold lines on the existing Mission 1 live camera overlay, preserving the accepted trigger semantics and runtime behavior.

## Baseline and rollback checks
- Verified current GitHub `CustomDrive` source blobs match the uploaded `PiDrive-main.zip` baseline.
- Reviewed latest and previous three CustomDrive notes: `0_5_13`, `0_5_14`, `0_5_15`, `0_5_16`.
- Preserve the accepted Mission 1 interpretation **100% = top / 0% = bottom**, pickup class mapping, stop-before-grip/release, moving camera updates, model/arm/motor controls, motor calibration and remembered settings.
- No mission state-machine or motor command code was modified.

## Files changed
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/custom_drive/mission1_session_app.py` (version marker only)
- `CustomDrive/tests/test_mission1_trigger_guides.cjs` (new)
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_17.md` (new)

## Exact behavior changed
1. The Pi-generated live preview now has a distinguishable **green Grip** line and **amber Drop-off** line, each with a matching percent label.
2. Both guides use the existing backend convention: ratio 1.0 = frame top and 0.0 = frame bottom. SVG top-origin Y is calculated as `round(height * (1 - ratio))` and clamped to the frame.
3. The grip label sits at the left edge and the drop-off label at the right edge, so identical thresholds can display both names without overlapping. Text uses an outline for readability on a busy camera image.
4. SVG coordinates scale with the preview's `viewBox` without a separate fixed-resolution overlay. The original deadband, center axes, target-dot overlay, and detection behavior remain present.
5. The Mission 1 version marker is updated from `0_5_16` to `0_5_17` so browsers refresh cached JS/CSS.

## Verification actually performed
- `node --check custom_drive/mission1_web/static/app.js` → passed.
- `node tests/test_mission1_trigger_guides.cjs` → passed in fake SVG DOM. Tests check boundary/intermediate percentages, clamping, invalid-input fallback, independent colored labels, coincident thresholds, `viewBox` sizing, and preservation of target-center dots.
- `python -m py_compile custom_drive/mission1_session_app.py` → passed.
- Compared prior four patch notes and original GitHub file SHAs before editing.

## Known limits
- No live Raspberry Pi camera UI test or real servo/motor test was performed.
- This is a **visual-only** update: it does not change grip/release trigger logic or confirm a physical grip.
- Future UI work may add user-toggleable guide visibility and enhanced small-screen labels, if required.
