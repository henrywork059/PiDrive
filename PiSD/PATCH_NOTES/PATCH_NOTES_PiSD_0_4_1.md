# PATCH NOTES — PiSD_0_4_1 Code-Level Cleanup Review

## Request summary

The user asked for a detailed whole-project PiSD code-level review to find conflicts, bugs, unexpected behaviour, and redundancy. The user also requested that redundant or currently-unused code should not be deleted, but should be commented out so it is not active right now.

## Source baseline

- Started from uploaded stable package: `PiSD_0_4_0.zip`.
- Checked the latest baseline note `PATCH_NOTES_PiSD_0_4_0.md` and recent accepted `0.3.x` patch notes to avoid rolling back Manual Drive, recording, settings, responsive layout, and camera/motor behaviour.

## Findings

No critical coding-level conflict was found in the active runtime path during local static validation. The main issues found were small cleanup items:

1. `pisd/core/settings_manager.py` imported `ok_payload` and `report_payload`, but the settings manager does not build HTTP responses directly.
2. `pisd/web/static/js/main_dashboard.js` still had an unused `refreshFrame()` snapshot helper, while the current dashboard preview path uses MJPEG live preview.
3. Several validation scripts had imports left over from earlier drafts that are not used by the current test code.

These are not runtime-breaking bugs, but they add noise and can mislead future debugging.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/scripts/test_motor_channels.py`
- `PiSD/scripts/test_panel_testing_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_1.md`

## Exact behaviour changed

### Version metadata

- Updated package version from `0.4.0` to `0.4.1`.

### Settings manager cleanup

- Stopped actively importing unused HTTP payload helpers in `settings_manager.py`.
- Left a commented note showing the older planned import path instead of deleting it silently.
- No settings schema, persistence, normalisation, or runtime apply behaviour was changed.

### Main Dashboard cleanup

- Commented out the unused `refreshFrame()` snapshot helper in `main_dashboard.js`.
- Left a clear note that it can be restored only if a future dashboard snapshot-mode button returns.
- The current `startLivePreview()` MJPEG path remains active.
- No Manual Drive preview/camera/recording behaviour was changed.

### Test script cleanup

- Commented out unused imports in:
  - `scripts/test_motor_channels.py`
  - `scripts/test_panel_testing_page.py`
  - `scripts/test_settings_persistence.py`
- Test logic was not removed.

## Anti-rollback check

Confirmed this patch does not remove or roll back the recent accepted behaviour from `0.3.8`, `0.3.9`, `0.3.10`, or stable `0.4.0`:

- Manual speed and steer strength still support `1.0`.
- Manual Drive status/run signals remain present.
- The smaller drag-pad knob remains unchanged.
- The Manual Drive `Snapshot view` button remains removed.
- Recording/snapshot folder list, zip download, and delete APIs remain unchanged.
- Settings persistence and shared presentation settings remain unchanged.
- Responsive layout contract remains unchanged.

## Verification actually performed

Executed locally in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Observed result:

- Python compile check passed.
- `PiSD.py --status-only` returned a normal simulation status.
- Manual Drive static/source contract passed.
- Settings persistence validation passed.
- Front page/settings/manual tab static validation passed.
- UI presentation consistency validation passed.
- Standard validation passed with API/camera/motor hardware checks skipped.

## Not verified here

- Full Flask API test client execution, because Flask is not installed in this packaging environment.
- Real Pi browser rendering.
- Real OV5647 camera capture.
- Real GPIO motor output.

## Known limits / next steps

- This is a conservative cleanup patch, not a broad refactor.
- Intentional future placeholder panels in the Panel Testing page were left active because current docs and tests explicitly describe them as intentional planning placeholders.
- Hardware/API validation should be run on the Raspberry Pi after applying the patch.
