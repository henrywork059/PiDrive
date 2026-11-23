# PiServer 0_4_25 — R46 terminology and actionable empty states

## Request and acceptance
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` R46: short text that tells an operator **what action happens, where, and whether hardware is involved**, plus **one useful next action** for empty/busy/offline/permission/error states. Preserve behavior and avoid crowding camera/preview panels. This component's edits are deliberately copy-only except the existing version marker and additive tests.

## Live baseline and anti-rollback review
- **Exact direct parent:** R45 draft #64 / update/piserver-0_4_24-r45-style-contract / feca560810dcb01a5c0f8f805051d0b74df30503. R46 branch `update/piserver-0_4_25-r46-empty-states` was created at the parent head; it remains a stacked **draft**, not merged into main.
- Inspected actual component entrypoint and current UI files before editing, and reviewed current note plus previous three for this component: 0_4_24 (R45 style), 0_4_23 (R43 polling), 0_4_22 (R36 responsive), 0_4_21 (R35 accessibility).
- No UI redesign, placeholder-only substitute, cross-component stylesheet, baseline ZIP overwrite, runtime/config value reset, motor/safety/permission changes, or file-tree reorganization.

## Root cause
An empty model dropdown, unhelpful `No model action` and `No folder selected` text lacked recovery; generic HTTP fallback concealed whether login, permission or server connection was required.

## Files changed / exact behavior
- `PiServer/piserver/web/static/app.js`: empty model and recording option now names Upload or Record/Refresh; model load/delete selectors give distinct steps; HTTP fallback distinguishes 401 login, 403 permission, 5xx Pi offline, and invalid inputs. Existing 401 redirect remains. Read-only status poll fallback adds connection/retry guidance. No motor, camera or preview algorithm touched.
- `PiServer/piserver/web/templates/index.html`: concise first-load model/recording help without adding widgets.
- `PiServer/piserver/app.py`: `APP_VERSION` 0_4_24 → 0_4_25 only.
- `PiServer/tests/test_ui_copy_r46.cjs`: seven source/syntax/safety checks.
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_25.md`: this note.

## Verification actually performed
- 7/7 exact committed JS test callbacks executed in isolated V8 compatibility harness against live GitHub files, including JavaScript syntax parsing and STOP/polling/freshness source guards.
- **Direct-parent GitHub comparison completed:** 5 files changed (2 new, 3 modified); 0 commits behind R45, no deleted paths or edits outside PiServer; camera/motor/config services, theme, R43 status/preview scheduling and R45 preference code untouched.
- Tests that **remain outstanding**: native `node --test` or Python `unittest` on a checked-out current branch, full component suites, browser interaction/screenshots, live Raspberry Pi motor/camera/network or Windows Qt integration. V8 test callbacks are not native Node's test runner.
- Version marker only advances this component's existing version series; saved config and user data stay intact.

## Release gate
- Run `node --test PiServer/tests/test_ui_copy_r46.cjs` against the exact PR branch, plus full component test suites.
- Open model/recording panels with no files, check 401/403/5xx and offline browser behavior, Upload/Load/Delete flows, STOP, 60 ms control tick, R43 preview/status and R45 saved style. Full Python/browser/physical Pi tests still needed.
- Check that a successful operation is reported as *confirmed* only after real backend success; a front-end Copy/Preview/Select change cannot mutate motor/servo behavior.
- Merge only after human review and explicit authorization. R46 must not be merged ahead of its parent stack.
