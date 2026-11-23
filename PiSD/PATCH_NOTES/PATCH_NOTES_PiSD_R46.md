# PiSD 0.11.19 — R46 terminology and actionable empty states

## Request and acceptance
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` R46: short text that tells an operator **what action happens, where, and whether hardware is involved**, plus **one useful next action** for empty/busy/offline/permission/error states. Preserve behavior and avoid crowding camera/preview panels. This component's edits are deliberately copy-only except the existing version marker and additive tests.

## Live baseline and anti-rollback review
- **Exact direct parent:** R43 draft #61 / update/pisd-r43-adaptive-stream-throttle / 047f385c13dc7923a495b11fc6f1e8ac3bedd96d. R46 branch `update/pisd-r46-terminology-empty-states` was created at the parent head; it remains a stacked **draft**, not merged into main.
- Inspected actual component entrypoint and current UI files before editing, and reviewed current note plus previous three for this component: R43 hidden MJPEG, R36 responsive controls, R35 Space/STOP keyboard, R32 operating readiness.
- No UI redesign, placeholder-only substitute, cross-component stylesheet, baseline ZIP overwrite, runtime/config value reset, motor/safety/permission changes, or file-tree reorganization.

## Root cause
Recording/snapshot folders and model dropdowns reported `No folders` / `No files` without a next action; offline listing failures surfaced raw exception text rather than a short connection/Refresh instruction. AI preview errors gave no recovery step.

## Files changed / exact behavior
- `PiSD/pisd/web/static/js/manual_drive.js`: no recordings → Start live then Record; no snapshots → Start live then Capture. Display model avoids false `Loaded 0...` success when both collections empty; failed folder refresh shows one Pi connection/Refresh instruction while retaining the existing coded diagnostics log.
- `PiSD/pisd/web/static/js/ai_mode.js`: empty model list identifies accepted `.keras`/`.tflite` upload, missing selection identifies Choose, preview error says check camera and Start live. Existing AI/control loops and stop beacons untouched.
- `PiSD/pisd/__init__.py`: 0.11.18 → 0.11.19.
- `PiSD/scripts/test_ui_copy_r46.cjs`: seven JS syntax/copy/safety guards.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R46.md`: this note.

## Verification actually performed
- 7/7 exact committed JS test callbacks executed in isolated V8 compatibility harness; both modified browser files parsed and R43 MJPEG/STOP/AI-status safety strings remained.
- Direct-parent GitHub comparison and no-rollback checks must be completed before opening the draft PR; do not claim checks not performed.
- Tests that **remain outstanding**: native `node --test` or Python `unittest` on a checked-out current branch, full component suites, browser interaction/screenshots, live Raspberry Pi motor/camera/network or Windows Qt integration. V8 test callbacks are not native Node's test runner.
- Version marker only advances this component's existing version series; saved config and user data stay intact.

## Release gate
- Run `node --test PiSD/scripts/test_ui_copy_r46.cjs` against the exact PR branch, plus full component test suites.
- Use actual Pi camera and UI to try empty recording/snapshot listings, offline file refresh, no model, model upload, preview error, Space STOP, global AI stop, hide/restore MJPEG; run full PiSD tests and browser screenshots.
- Check that a successful operation is reported as *confirmed* only after real backend success; a front-end Copy/Preview/Select change cannot mutate motor/servo behavior.
- Merge only after human review and explicit authorization. R46 must not be merged ahead of its parent stack.
