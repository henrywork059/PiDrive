# PiSD 0.11.13 — U28 safety status and explicit camera-fault rearm

## Request
A consistent, additive safety status shape and explicit safe rearm for PiSD, retaining independent PiSD control/camera/model services and previous U21/U27 protections.

## Root cause
U21's stale-frame latch stopped AI motor output, but `AIDriveService.stop()` and `start()` reset the latch automatically. A simple restart could therefore bypass fault acknowledgement while the camera was still stale.

## Files changed
- `pisd/services/ai_drive_service.py`: persistent camera-fault latch, verified fresh-frame/zero-motor rearm, worker join check, schema-v1 safety status.
- `pisd/app.py`: additive safety status in existing status responses, safety endpoints, and motion guards for manual/tuning/test routes.
- `pisd/__init__.py`: 0.11.13 version marker.
- `scripts/test_safety_rearm.py`: self-contained service tests.
- `README.md` and this patch note.

## Behavior
All safety statuses use `schema_version=1`, `component`, `state`, `latched`, `motion_allowed`, `rearm_required`, `rearm_available` and `reason`. Existing root API keys remain unchanged. `GET /api/safety/status` reads the contract, `POST /api/safety/rearm` accepts only `{"confirm":true}`. When camera data stops advancing, stop and start do **not** silently clear the latch. Rearm requires a stopped AI worker, camera already running, **a newly arriving JPEG frame** and motor stop; if checks fail, latch remains active. AI drive, manual nonzero movement, and motor tuning/test are refused while latched. Read-only status/config and STOP remain usable. After successful rearm, a new AI drive start still requires its prior safety acknowledgement.

## Compatibility and verification
Based on draft PR #30 (0.11.12), itself stacked on #26, #22, #20 and #12. Preserves model manifests/rollback, recording protection/recovery, AI performance metrics, and current UI. No saved config changed. Regression tests added, but **full stacked Flask suite and Raspberry Pi camera/motor verification were not run** in this environment.

## Known limits
A new JPEG sequence during rearm demonstrates frame progress, not valid road perception or physical motor de-energization. Hardware tests must confirm timeout → STOP → new frames → acknowledged rearm → fresh drive command.
