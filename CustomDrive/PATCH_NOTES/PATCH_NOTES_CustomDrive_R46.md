# CustomDrive GUI 0_3_17 / Mission 1 0_5_27 — R46 terminology and actionable empty states

## Request and acceptance
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` R46: short text that tells an operator **what action happens, where, and whether hardware is involved**, plus **one useful next action** for empty/busy/offline/permission/error states. Preserve behavior and avoid crowding camera/preview panels. This component's edits are deliberately copy-only except the existing version marker and additive tests.

## Live baseline and anti-rollback review
- **Exact direct parent:** R45 draft #65 / update/customdrive-r45-style-contract / 6d3253d4ad835530829bff4036b7c4857e73d9f2. R46 branch `update/customdrive-r46-terminology-empty-states` was created at the parent head; it remains a stacked **draft**, not merged into main.
- Inspected actual component entrypoint and current UI files before editing, and reviewed current note plus previous three for this component: R45 separate design tokens, R44 trigger guide/saved readback, R43 polling, R36 compact layouts, R35 STOP/focus, R33 mission timeline.
- No UI redesign, placeholder-only substitute, cross-component stylesheet, baseline ZIP overwrite, runtime/config value reset, motor/safety/permission changes, or file-tree reorganization.

## Root cause
`Toggle Preview` obscured the browser camera action; `Deploy Model` did not name the Pi destination, and empty selectors, 403/5xx fallbacks and disconnected progress gave generic or non-actionable text.

## Files changed / exact behavior
- `CustomDrive/custom_drive/gui_web/static/app.js`: explanatory no-model picker, actionable Deploy retry and 401/403/5xx HTTP fallback; preserves backend-provided error details, pending-versus-deployed rules and STOP/Apply logic.
- `.../gui_web/templates/index.html`: rename only preview button to `Start / Stop Camera Preview` and Deploy button to `Deploy Model to Pi`; retain IDs and events.
- `.../mission1_web/static/app.js`: no-model upload/choose step, distinct permission/connection fallbacks, no-detection and disconnected-timeline next actions; keep R44 Save readback and R43 polling.
- `.../mission1_web/templates/index.html`: model selection/upload buttons say Pi destination, keep same IDs.
- `custom_drive/gui_control_app.py`, `mission1_session_app.py`: GUI 0_3_16 → 0_3_17; Mission 1 0_5_26 → 0_5_27 (version lines only).
- `CustomDrive/tests/test_ui_copy_r46.cjs`: seven copy/syntax and preserved R43/R44 checks.
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R46.md`: this note.

## Verification actually performed
- 7/7 exact committed JS test callbacks executed through V8 compatibility harness with live source, including both scripts' syntax, fail/retry wording, Pi action labels and retained saved-value/STOP guards.
- **Direct-parent GitHub comparison completed:** 8 files changed (2 new, 6 modified); 0 commits behind R45, no deleted paths or edits outside CustomDrive; configs, motor/servo/mission services, R43 frame scheduler, R44 guide math, R45 theme and layout CSS untouched.
- Tests that **remain outstanding**: native `node --test` or Python `unittest` on a checked-out current branch, full component suites, browser interaction/screenshots, live Raspberry Pi motor/camera/network or Windows Qt integration. V8 test callbacks are not native Node's test runner.
- Version marker only advances this component's existing version series; saved config and user data stay intact.

## Release gate
- Run `node --test CustomDrive/tests/test_ui_copy_r46.cjs` against the exact PR branch, plus full component test suites.
- Check GUI Deploy to Pi actually deploys/STOP terminates, preview toggle correctly updates label/visual status, Mission 1 empty detection/model and disconnect, server permission errors, R44 trigger Save/Start guard, R43 polling, R35 keyboard/arm stop, R36 phone widths; run full tests.
- Check that a successful operation is reported as *confirmed* only after real backend success; a front-end Copy/Preview/Select change cannot mutate motor/servo behavior.
- Merge only after human review and explicit authorization. R46 must not be merged ahead of its parent stack.
