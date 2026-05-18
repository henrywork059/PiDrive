# PiSD 0.5.12 Patch Notes

## Request summary
Patch the duplicate/confusing speed, throttle, safety, and legacy-control issues found in the PiSD 0.5.11 review.

## Cause / root cause
Several safety and speed policies had grown in parallel across Manual Drive, AI Mode, Dashboard, settings persistence, and service-layer clamps. Some repetition is intentional as a final safety guard, but several policy-level checks were only enforced in the browser or were duplicated with different limits. The older Dashboard shell also still looked like a normal current driving page even though Manual Drive and AI Mode are now the active workflows.

## Files changed
- `README.md`
- `docs/ERROR_CODES.md`
- `pisd/__init__.py`
- `pisd/app.py`
- `pisd/core/settings_manager.py`
- `pisd/services/ai_drive_service.py`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/js/main_dashboard.js`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/templates/front_page.html`
- `pisd/web/templates/main_dashboard.html`
- `scripts/test_ai_drive_service.py`
- `scripts/test_settings_persistence.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_5_12.md`

## Exact behaviour changed
- `/api/control/manual` now applies the saved `manual_drive.max_speed_limit` before sending values into `MotorService`.
- `/api/control/manual` now refuses non-zero hardware manual commands unless the request includes live `safety_ack` and `enable_motor_output`.
- Manual Drive browser commands now send live `safety_ack` and `enable_motor_output` when the safety checkbox is enabled.
- Manual Drive no longer sends `steer_mix: 1.0` as a per-command override. `MotorService` now uses the saved motor `steer_mix` setting as the single motor-mixing policy source.
- The older Dashboard manual buttons also stop overriding `steer_mix` and send live safety flags.
- Manual Drive overlay curve control now matches backend settings: max `5.0`, default `3.35`, path-width default `0.34`.
- AI steering-only mode now keeps `fixed_throttle` even when predicted steering is nearly straight. It no longer stops just because the model output is straight.
- AI `motor_output_enabled` is now session-only. It is no longer saved into `runtime_settings.json`, and old saved `true` values are normalised back to `false` on load/save.
- AI Mode no longer restores the motor-output checkbox from saved config. It is cleared on first page render only, so a Save action does not unexpectedly uncheck the live box immediately before Start AI Drive reads it.
- Dashboard is labelled as a legacy/development comparison shell from the front page and dashboard subtitle.
- Dashboard old manual/channel speed limits were raised to full-scale `1.0` to avoid conflicting with the current Manual Drive full-scale behaviour.
- README and error-code docs now describe the current 0.5.12 safety/speed policy.

## Verification actually performed
- `python3 -m compileall -q pisd scripts`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `node --check pisd/web/static/js/main_dashboard.js`
- `python3 scripts/test_ai_drive_service.py`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_front_page_tabs.py --static-only`
- `python3 scripts/test_main_dashboard.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Full Flask route/API tests were not run because Flask is not installed in this container.
- Real Raspberry Pi camera/motor hardware tests were not run in this container.

## Known limits / next steps
- Shared overlay, API, and status helper logic is still duplicated across Manual Drive, AI Mode, and Dashboard. This patch fixes the high-risk policy conflicts first; a later patch should centralise shared JS helpers.
- Camera config source-of-truth is still duplicated between backend config, service dataclass, UI forms, and diagnostic scripts. A later patch should introduce/expand a schema endpoint and make UI limits follow it.
- Dashboard remains a legacy/development shell. It is clearly labelled and speed limits were updated, but its preview overlay is not fully modernised to the Manual Drive/AI road-guide overlay.
