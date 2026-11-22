# PiServer 0_4_18 — U28 common safety status and checked rearm

## Request
Expose a predictable safety status contract and an explicit, fail-closed rearm operation, without merging PiServer with the independent PiSD or CustomDrive runtime.

## Root cause
The legacy `/api/system/estop` accepted `enabled=false` without explicit confirmation and the status API had only the legacy `safety_stop` flag. Clearing the latch could return to the previously selected automatic algorithm.

## Changed files
- `piserver/services/control_service.py`: additive schema-v1 safety status; checked rearm resets motor commands, input lease and active algorithm before releasing the latch.
- `piserver/app.py`: `GET /api/safety/status`, `POST /api/safety/rearm`, guarded legacy E-stop toggle, and version marker.
- `piserver/web/static/app.js`: explicit operator confirmation when clearing E-stop.
- `tests/test_safety_rearm_contract.py`: contract, confirmation, zero-command, and stop-failure regression tests.
- `README.md`: U28 safety API documentation.
- This patch note.

## Behavior
`safety` is an **additive** object in the existing `/api/status` response; legacy keys remain. Its fields match the U28 contract: `schema_version=1`, `component`, `state`, `latched`, `motion_allowed`, `rearm_required`, `rearm_available`, `reason`.

Rearm requires a JSON object with `confirm: true` (a JSON boolean; strings/numbers are refused), the controller loop running, and a successful motor zero-stop. Before the latch is released, the active algorithm becomes manual, stale controls are zeroed, and the manual-command lease is invalidated. Failed rearm leaves E-stop latched. Existing E-stop UI now asks for operator confirmation and uses the checked route.

## Compatibility and verification
Built forward on draft PR #31 (0_4_17), which already contains U27/U26/U23/U14/U12/F3/F1 work. No saved configuration file is touched. Tests are provided; the full stacked suite and Raspberry Pi motor behavior were **not run** in the GitHub connector environment.

## Remaining limits
Local status and unit tests cannot prove physical GPIO de-energization. Verify E-stop, confirmed rearm, and a fresh post-rearm manual command on Raspberry Pi before merging.
