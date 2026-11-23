# CustomTrainer 0_2_17 — R46 terminology and actionable empty states

## Request and acceptance
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` R46: short text that tells an operator **what action happens, where, and whether hardware is involved**, plus **one useful next action** for empty/busy/offline/permission/error states. Preserve behavior and avoid crowding camera/preview panels. This component's edits are deliberately copy-only except the existing version marker and additive tests.

## Live baseline and anti-rollback review
- **Exact direct parent:** R42 draft #58 / update/customtrainer-0_2_16-r42-result-visibility / e913eec5bd2373abee632ddb3635fb3cb9886bc9. R46 branch `update/customtrainer-0_2_17-r46-empty-states` was created at the parent head; it remains a stacked **draft**, not merged into main.
- Inspected actual component entrypoint and current UI files before editing, and reviewed current note plus previous three for this component: 0_2_16 R42 result panel, 0_2_15 R41 annotation shortcuts, 0_2_14 U27 export manifest, 0_2_13 U25 immutable dataset cache.
- No UI redesign, placeholder-only substitute, cross-component stylesheet, baseline ZIP overwrite, runtime/config value reset, motor/safety/permission changes, or file-tree reorganization.

## Root cause
Native/Export Validate preview placeholders gave only `No preview` and task-blocking dialogs returned generic `Busy`/`Choose weights`; Pi deployment bundle messages could be mistaken for actual live deployment.

## Files changed / exact behavior
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`: actionable no-source, missing image folder, no-predictions, Busy and .pt/dataset prerequisites.
- `.../ui/pages/export_validate_page.py`: matching exported-model task-specific wording and Run Exported Validation next step. Read-only R42 result panel unchanged.
- `.../ui/pages/pi_deploy_page.py`: clarify export prerequisite, bundle output directory and that a generated folder is for copying to the Pi, not a live Pi mutation.
- `.../ui/main_window.py`: existing title version 0_2_16 → 0_2_17.
- `CustomTrainer/tests/test_ui_copy_r46.py`: eight stdlib AST/copy preservation tests.
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_17.md`: this note.

## Verification actually performed
- 18/18 actual source-contract checks passed against live GitHub files, including task-result panel preservation and separate native/exported vocabulary. Eight Python AST cases committed but not run against exact checkout.
- Direct-parent GitHub comparison and no-rollback checks must be completed before opening the draft PR; do not claim checks not performed.
- Tests that **remain outstanding**: native `node --test` or Python `unittest` on a checked-out current branch, full component suites, browser interaction/screenshots, live Raspberry Pi motor/camera/network or Windows Qt integration. V8 test callbacks are not native Node's test runner.
- Version marker only advances this component's existing version series; saved config and user data stay intact.

## Release gate
- Run `cd CustomTrainer && python -m unittest discover -s tests -p 'test_ui_copy_r46.py' -v` against the exact PR branch, plus full component test suites.
- Run Windows Qt and full CustomTrainer suites: missing .pt and exported model, missing dataset.yaml, busy, prediction without source, Pi bundle, R42 run states/Verified Open Location, R41 undo/redo, U27 manifest, U25 cache.
- Check that a successful operation is reported as *confirmed* only after real backend success; a front-end Copy/Preview/Select change cannot mutate motor/servo behavior.
- Merge only after human review and explicit authorization. R46 must not be merged ahead of its parent stack.
