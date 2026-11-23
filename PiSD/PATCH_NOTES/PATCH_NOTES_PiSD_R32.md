# PiSD 0.11.15 — R32 operating-mode readiness and control source

## Request summary
Implement roadmap R32 on both Manual Drive and AI Mode: one compact, read-only strip showing **camera state, selected/loaded model, current backend motor-command source, motor-output authorization, and the active stop reason or next action**. The UI must not replace the existing safety checkbox or interfere with global Space STOP.

## Root cause
Previously, an operator had to infer the difference between AI drive, preview-only inference, correction, direct manual commands, and motor-stop/safety-latch states by combining several panes and logs. The motor status exposed the last requested steering/throttle but not which *accepted command path* last wrote it. Frontend page/tab selection alone is not reliable evidence of backend motor ownership.

## Live baseline and anti-rollback
Built directly on **unmerged PiSD R31 draft PR #39** (`update/pisd-r31-settings-feedback`), itself stacked on U29 PR #35 and U28 PR #32, NOT main and not the older uploaded ZIP. Reviewed patch notes R31, U29, 0.11.13, 0.11.12, 0.11.11, and 0.11.10. Inspected real launcher `PiSD/PiSD.py`; `pisd/app.py` for `GET /api/status`, `GET /api/ai/status`, `POST /api/control/manual` and STOP; camera/motor/AI service status and command paths; both actual HTML/JS files and global Space STOP script. No new control route and no settings schema changes.

This patch preserves R31 backend-confirmed settings and retry, U29 replay, U28 latched camera-fault/rearm, U27 model preflight and rollback, U26 storage safety, existing AI/manual correction/mixing, overlays, recordings, single checkbox, control-pad shortcuts, motor stop behavior and separate capture/preview/AI rates.

## Files changed
- `PiSD/pisd/services/motor_service.py` — optional keyword-only diagnostic `control_source` for `update`; stable enumerated values `manual`, `manual_assist`, `ai`, `other`. The existing positional arguments and mixing are unchanged. Stopping resets the last-command source to `stopped`. This field appears only inside the already-existing status `motor.last_command` object.
- `PiSD/pisd/services/ai_drive_service.py` — tag actual authorized AI motor-update calls `ai`.
- `PiSD/pisd/app.py` — tag actual accepted `/api/control/manual` commands `manual` or `manual_assist` when assist payload is present. Existing safety gates, manual override-to-preview and response shapes unchanged.
- `PiSD/pisd/web/templates/ai_mode.html`, `manual_drive.html` — inline compact strip inserted into existing AI workflow/status panel; existing controls untouched.
- `PiSD/pisd/web/static/js/ai_mode.js`, `manual_drive.js` — render server-derived health/model/owner/safety; low-rate read-only polling even when AI is not running. AI's existing 250ms active status poll is reused, not duplicated. Polls are skipped while hidden, do not overlap, and show **Unconfirmed** on network/HTTP failure. Neither poll calls a motor endpoint.
- `PiSD/pisd/web/static/js/operating_readiness.js` (new) — pure status projection for both screens, separate selected model vs actually loaded model and AI preview vs actual drive. Correction is an active owner only if backend reports `manual_correction.active`; manual/assist is an active owner only for nonzero last-intended output and a tagged accepted command. If no motor command, the selected UI mode is shown explicitly as **idle**, not as active motor ownership.
- `PiSD/pisd/web/static/css/operating_readiness.css` (new) — small responsive four-field grid and one-line reason, inheriting page fonts/theme.
- `PiSD/pisd/__init__.py` — 0.11.15 version/cache key.
- `PiSD/scripts/test_operating_readiness.cjs` (new) — 32 deterministic pure projection cases.
- `PiSD/scripts/test_operating_control_source.py` (new) — seven simulation-only backend source/stop/mix regression cases for the actual MotorService class (provided for local test runs; not run in the current connected GitHub environment).
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R32.md` — this note.

## Safety / exact semantics
The strip is **diagnostic only**. A model selected in the file dropdown is not reported as loaded until the server says `model_ready=true`. AI preview never claims to own motor drive; AI + correction requires the backend-reported active correction, not merely an open Correction tab. Manual command source labels come from the last accepted backend motor update and are shown as active only when motor status reports nonzero intended output. `safety.latched` has absolute display priority. Simulated motors are never presented as physically energized. One safety confirmation checkbox remains authoritative for user intent, and existing backend per-command acknowledgement and explicit rearm requirements still apply. STOP/Space shortcuts and motor service output controls are not modified.

No config or persisted runtime data files touched. This does not introduce a control lease or change motor authorization, so `last_command.control_source` is diagnostic provenance, not a lock/lease guarantee.

## Verification actually performed
- **32/32** deterministic JS projection tests executed against the exact GitHub branch helper and test source via a V8 CommonJS-compatible harness; explicit source safety tests cover offline, safety latch, active correction, preview-only, manual/assist and simulation.
- Both final controller scripts and the helper parsed successfully in V8 as JavaScript. Expected HTML bindings and backend source metadata checked by source inspection.
- Compared the final branch against PR #39 to check for missing prior accepted files and cross-component changes; results appear in draft PR description.

**Not performed:** `python3 -m unittest scripts/test_operating_control_source.py`, Python syntax compilation in the branch runtime, a full Flask/hardware integration suite, real Raspberry Pi 4 camera/motor test, or browser visual accessibility testing.

## Known limits / next steps
Backend motor status reports **last motor intent and the last accepted command source**, not a hardware feedback signal or exclusive control lease. The strip explicitly separates selected/idle and active command states. Camera `running` plus a nonzero `frame_seq` indicates the camera published at least one frame, not that every displayed frame is fresh. Physical camera freshness/motor feedback remain covered by existing safety checks rather than UI inference. Test on Raspberry Pi with simulated and physically disconnected camera, existing E-stop/rearm and both Manual and AI Modes before promoting from draft.
