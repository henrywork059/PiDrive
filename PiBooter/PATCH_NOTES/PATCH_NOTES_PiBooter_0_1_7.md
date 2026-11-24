# PiBooter 0_1_7 — R46 terminology and actionable empty states

## Request and acceptance
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` R46: short text that tells an operator **what action happens, where, and whether hardware is involved**, plus **one useful next action** for empty/busy/offline/permission/error states. Preserve behavior and avoid crowding camera/preview panels. This component's edits are deliberately copy-only except the existing version marker and additive tests.

## Live baseline and anti-rollback review
- **Exact direct parent:** R36 draft #52 / update/pibooter-0_1_6-responsive-verification / bcf55619c8d2eda730ed09e034fbb30944b856ad. R46 branch `update/pibooter-0_1_7-r46-wifi-empty-state` was created at the parent head; it remains a stacked **draft**, not merged into main.
- Inspected actual component entrypoint and current UI files before editing, and reviewed current note plus previous three for this component: 0_1_6 R36 mobile Wi-Fi Choose, 0_1_5 R35 keyboard access, 0_1_4 R34 onboarding states, 0_1_3 U19 secure hotspot.
- No UI redesign, placeholder-only substitute, cross-component stylesheet, baseline ZIP overwrite, runtime/config value reset, motor/safety/permission changes, or file-tree reorganization.

## Root cause
Initial Wi-Fi scan, saved-profile, network-device and hotspot-client empty states lacked a single concrete action. Existing onboarding already distinguishes network auth errors and hotspot reconnection, so the patch does not replace those security-sensitive messages.

## Files changed / exact behavior
- `PiBooter/pibooter/app.py`: empty nearby network → Refresh scan or manual SSID; no saved profiles → Connect Pi; no adapter → check Pi adapter; no hotspot clients → connect phone to setup hotspot. Keep HTML escaping, SSID confirmation, CSRF, origin restrictions, hotspot timing and page geometry unchanged. Version header `PiBooter/0.1.6` → `PiBooter/0.1.7`.
- `PiBooter/tests/test_ui_copy_r46.py`: seven Python stdlib AST and security-string source checks.
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_7.md`: this note.

## Verification actually performed
- 8/8 live-source checks passed (message availability and CSRF/permission guard strings). Seven Python tests committed, not run on the exact GitHub checkout; no wireless hardware or browser tests done.
- **Direct-parent GitHub comparison completed:** 3 files changed (2 new, 1 modified); 0 commits behind R36, no deleted paths or edits outside PiBooter; NetworkManager commands, provisioning/CSRF security, config persistence, hotspot lifetime and R35/R36 responsive styles untouched.
- Tests that **remain outstanding**: native `node --test` or Python `unittest` on a checked-out current branch, full component suites, browser interaction/screenshots, live Raspberry Pi motor/camera/network or Windows Qt integration. V8 test callbacks are not native Node's test runner.
- Version marker only advances this component's existing version series; saved config and user data stay intact.

## Release gate
- Run `cd PiBooter && python -m unittest discover -s tests -p 'test_ui_copy_r46.py' -v` against the exact PR branch, plus full component test suites.
- Run all PiBooter tests and actual Raspberry Pi hotspot: empty scan, Refresh, manual hidden SSID, saved profile, no Wi-Fi adapter, no clients, timed setup exit, 401/403/CSRF and R35/R36 mobile keyboard; do not reveal hotspot password.
- Check that a successful operation is reported as *confirmed* only after real backend success; a front-end Copy/Preview/Select change cannot mutate motor/servo behavior.
- Merge only after human review and explicit authorization. R46 must not be merged ahead of its parent stack.
