# CustomDrive GUI 0_3_14 and Mission 1 0_5_23 — R36 responsive verification

## Request
Implement R36 responsive layout validation for existing CustomDrive GUI and Mission 1 at 390/768/1024/1440 px. Fix genuinely narrow-screen toolbar, dialog, long-label and table scrolling risks without redesigning layouts, changing runtime authority, or undoing R33/R35.

## Baseline and anti-rollback
- Based on unmerged R35 CustomDrive PR #47 `update/customdrive-r35-accessibility-parity` (which is based on R33 PR #43). **Must merge/review #43 before #47 before this PR.**
- Reviewed latest component notes R35, R33, R31 and R30. Actual launch files: `CustomDrive/run_custom_drive_web.py` (`run_custom_drive_gui.py` forwards here); **separate** Mission 1 entry `CustomDrive/run_mission1_stage_test_demo.py`. Host/port come from each existing config unless explicitly overridden.
- Preserve U28 safety/rearm, R29 replay, R30 decoded-frame freshness, R31 backend settings save/retry, R33 actual server-observed mission timeline, R35 keyboard-safe arm hold and manual STOP; preserve config values, grip pose semantics and motor control.

## Causes
- GUI `.topbar` had a fixed 54 px height at all sizes despite a wrapping group of status/settings buttons. At 390 px, those buttons can require an extra line and overlap the workspace.
- GUI settings `.modal-window` had max-height and an internal `.modal-body` but did not explicitly reserve a mobile scrollable flex child; on short viewports Save could end outside reach.
- Mission 1 already uses 16:9 camera and single-column grids at phone widths; long stage/Save/Stop labels and large tables could widen the full page instead of wrapping or scrolling locally.

## Files changed and precise behavior
- `custom_drive/gui_web/static/styles.css`: phone-only ≤600 px topbar height becomes auto to contain wrapped toolbar; workspace remains scrollable. Settings backdrop/window gains dynamic viewport max-height, with internal scrollable modal body so existing Save/Retry buttons can be reached. Manual STOP and toolbar labels get 44 px targets and wrapping. The existing square joystick aspect, panel grid and larger viewport geometry are unchanged.
- `custom_drive/mission1_web/static/styles.css`: phone-only ≤720 px reduce gutters, ensure panels and mission timeline can shrink, allow wide arm/data tables to scroll horizontally, and wrap existing Stop/Save/pose action labels. No change to the existing 16:9 viewer stage, R33 state history, or motor/arm controls.
- `custom_drive/gui_control_app.py` patch version **0_3_13 → 0_3_14**; `custom_drive/mission1_session_app.py` **0_5_22 → 0_5_23**; only asset cache labels changed.
- `CustomDrive/tests/test_responsive_r36.cjs` (new): 14 source-level regression cases for both active interfaces, R33/R35 preservation, safe action labels, 1:1 GUI pad and 16:9 Mission 1 preview.
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R36.md`: this note.

## Required viewport matrix
| Width | GUI toolbar/E-Stop/pad/modal Save | Mission 1 STOP/Save/preview/table/timeline | Screenshot |
|---|---|---|---|
| 390 | Phone header can grow; verify thumb reach | Scrollable arm table/long buttons | Pending |
| 768 | Verify layout stack and modal | Verify single column/table | Pending |
| 1024 | Verify two-column/row flow | Verify two-column views | Pending |
| 1440 | Preserve desktop arrangement | Preserve 16:9 viewer and summary | Pending |

Use the shared Playwright screenshot script `PiServer/tests/capture_responsive_r36.py`, suites `customdrive-gui` and `customdrive-mission1`, from the R35 parent then this R36 branch. Its source is in the independent PiServer R36 PR. The exact visual matrix instructions are in `PiServer/tests/R36_VIEWPORT_MATRIX.md`.

## Verification actually performed
- **14/14** deterministic source-level V8 tests passed against the final branch CSS/HTML/version source.
- GitHub diff vs R35 parent checked no cross-component changes/deletions and retained R33 stage timeline.
- **Not executed:** real live-app Playwright screenshots, baseline diffs, Flask/Python/servo/motor integration, touch and device accessibility. The screenshot runner itself has not been exercised against a live current branch in this environment.

## Limits / next steps
The responsive patch is intentionally presentational and does not fix a backend/network STOP lost after disconnect. Before merging, use actual live camera/arm disarmed test pages to capture all four widths, inspect every Save and STOP and validate R35 keyboard hold release separately.
