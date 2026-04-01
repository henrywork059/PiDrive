# PiDrive Bug Prevention Notes (Derived from Existing Patch Notes)

This file captures recurring bug patterns documented in project patch notes and turns them into preventive implementation checks.

## 1) CustomDrive Mission 1 detection box rendering issues

### Source pattern
Observed in the Mission 1 detector/overlay pipeline history (notably around the `0_4_x` patch line):
- 6-column detection output parsing did not consistently normalize/decode coordinates before frame scaling.
- `np.squeeze()` could collapse `(1, 6)` into `(6,)`, causing single-row detections to bypass expected parser paths.

### Affected areas
- `CustomDrive/custom_drive/mission1_tflite_detector.py`
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`

### Prevention checklist
- Validate tensor shape before branch logic:
  - if detection array is 1D with length 6, reshape to `(1, 6)`.
- Normalize parser contract:
  - convert all accepted input formats to a single internal box format (`xyxy` in model-input pixel space) before frame scaling.
- Add explicit format detection guards:
  - distinguish `xyxy` vs `xywh`
  - distinguish normalized (`0..1`) vs pixel-space values
- Add regression fixtures for:
  - single-row 6-column detection
  - normalized `xyxy`
  - normalized `xywh`
  - pixel-space `xyxy`
- Log one raw sample row in debug mode when parsed output appears out-of-range.

## 2) CustomTrainer Marking panel width regression

### Source pattern
Patch history indicates right-panel width could become too wide due to splitter defaults plus restored UI state.

### Affected areas
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`

### Prevention checklist
- Apply hard maximum width caps for tool panels.
- Keep default splitter ratios biased toward main preview canvas.
- Ensure restored splitter state is clamped to allowed min/max ranges.
- Prefer vertical stacking for long-label controls in narrow tool columns.
- Re-check panel behavior on common desktop widths before release.

## 3) PiServer dashboard layout density and saved-layout drift

### Source pattern
Patch notes indicate stale saved localStorage layouts and roomy defaults caused panel usability issues.

### Affected areas
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py` (version marker/cache-busting context)

### Prevention checklist
- When default panel geometry changes materially, bump saved-layout namespace key.
- Keep status/telemetry panel minimum dimensions compatible with narrow widths.
- Add/maintain responsive breakpoints for metric-card wrapping.
- During UI compaction updates, test for clipping in:
  - status cards
  - top banner
  - bottom utility controls
- Avoid mixing functional and visual changes in one patch when possible.

## 4) Release-note vs active-code mismatch

### Source pattern
Some patch notes report newer version numbers than currently embedded app constants.

### Prevention checklist
- Before publishing docs:
  - confirm version markers in code constants
  - confirm entry-point scripts and README commands still match repo files
- In release notes, state whether the patch is applied in the current branch or documented as forward/historical.
- Add a short “code marker check” section to release PRs for transparency.
