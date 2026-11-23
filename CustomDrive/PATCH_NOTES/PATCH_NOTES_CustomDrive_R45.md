# CustomDrive GUI 0_3_16 + Mission 1 0_5_26 — R45 UI design tokens and drift control

## Request
Implement CustomDrive portion of roadmap **R45**: document operator-style density, status colors, concise action/empty-state labels and future icon sizing per component, plus small regression checks to catch token drift and saved-preference resets. Keep the separate general GUI and Mission 1 styling owned in CustomDrive, with no shared runtime CSS import and no mass palette, geometry, settings or safety behavior changes.

## Live code and patch baseline
- Direct parent: **open/unmerged draft PR #62** R44, branch `update/customdrive-r44-trigger-threshold-legibility`, actual head SHA `1847b19f8fdc7ed3fe7c29d6aea09d33d137264f`. R44 depends on R43 #60, R36 #51, R35 #47 and R33 #43. R45 branch `update/customdrive-r45-style-contract` is layered on the exact parent; do not merge independently.
- Reviewed latest component patch notes **R44** (0_5_25 trigger ruler/0% gate fix), previous three **R43** (adaptive status/frame polling), **R36** (mobile layouts), **R35** (keyboard/focus/arm stop). R33 Mission 1 timeline and R30 preview freshness reviewed via live code.
- Inspected real launchers `CustomDrive/run_custom_drive_web.py` and `run_custom_drive_gui.py` (general GUI), `run_mission1_stage_test_demo.py` (separate Mission 1), `custom_drive/gui_control_app.py`, `mission1_session_app.py`, both web component CSS/JS, and the existing tests. No guessed entrypoints, paths, or versions.
- The current general-GUI `theme.js` is byte-identical with PiServer's on the live baseline, SHA `ca185fec09e6f02ce402a1ce1493d0f8c0ff935c`. Keep each file **component-owned**. The general GUI's historical `PiServerStyleCustom:v0_3_5` localStorage key/API is preserved exactly, not migrated.
- Real independent version lines: GUI **0_3_15 → 0_3_16** and Mission 1 **0_5_25 → 0_5_26**; both changes are to existing version constants only, no change to persisted config schema.

## Root cause
PiServer and CustomDrive share accepted general GUI theme values today, but cross-component copying or runtime imports would create unwanted rollback coupling. The standalone Mission 1 UI intentionally uses a different cyan/blue palette and state-themed timeline. New panels risk mixing color meanings (pending vs applied, safety failure vs active), inconsistent spacing, icon scaling and hard-coded style values that bypass the user's persisted GUI overrides. There was no confirmed runtime theme defect to repair.

## Files changed and exact behavior
1. `CustomDrive/UI_DESIGN_TOKENS.md` **new** — two component-specific contracts:
  - General GUI: semantic `--ok`/`--warn`/`--danger`/`--muted`, amber accent, `80%` font, 10/12px workspace/panel, 10px cards/fields, operator Save/Apply/STOP meaning, custom-override persistence.
  - Mission 1: *separate* blue/cyan dark palette, R33 current/completed/failed/interrupted timeline colors (blue/green/red/amber), R44 green Grip versus amber Drop-off ruler and honest draft/saved readout, 16:9 frame, R36 responsive margins and R35 keyboard focus.
  - New-icon guideline **16px inline, 18px toolbar and ≥44px touch target**, not an instruction to resize current icons or alter existing SVG.
2. `CustomDrive/tests/test_ui_style_tokens_r45.cjs` **new** — **14 deterministic Node smoke tests** for real general-GUI `theme.js` in a fake DOM/localStorage, status semantics, compact spacing, persisted overrides through reapply/reload/explicit reset, unchanged style API/key, and actual CSS selectors of GUI and standalone Mission 1 for statuses, timeline, R44 trigger colors/guide, focus and phone targets. No cross-component theme byte-equality requirement.
3. `CustomDrive/README.md`: link design policy, tests and clarify no UI/theme migration.
4. `CustomDrive/custom_drive/gui_control_app.py`: **only** increment `APP_VERSION 0_3_15 → 0_3_16`, preserving GUI endpoints and all R43 status/polling.
5. `CustomDrive/custom_drive/mission1_session_app.py`: **only** increment `APP_VERSION 0_5_25 → 0_5_26`; retains R44 0% grip/dropoff lookup corrections, config readback, mission safety, R43 status and frame scheduling.
6. `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R45.md`: this note.

**No edits** to either `theme.js` or `styles.css`, Mission 1 SVG rendering, HTML, page JS, R44 trigger behavior, R43 polling algorithms, R35 arm keyboard controls, R33 timeline, model/camera/motor/servo services, config persistence or user localStorage. No PiServer or piTrainer files included in this component PR.

## Verification actually performed
- Live GitHub source read and parent PR #62 verified draft/open with exact head before branch creation. Compared the two independent `theme.js` files by Git blob SHA to establish their *current* equality without hardcoding a perpetual equality policy.
- Actually **executed** both components' real unmodified theme scripts in isolated V8 fake DOM + localStorage and ran **18/18 combined assertions** (9 PiServer + 9 CustomDrive) for runtime theme defaults, status colors, font-scale derivation, custom preferences across apply/reload, explicit reset and corrupt stored-value fallback.
- Committed **14 new Node tests** but the **standalone Node file was not executed end-to-end** against a local checkout of this GitHub branch; no real browser screenshot, physical Pi model/arm/motor tests, or full Python test suite run.
- Final GitHub direct-parent compare and anti-rollback audit must be performed before opening draft PR.

## Release gate and limits
- Tests detect semantic role drift and persistence regressions, not pixel-perfect screenshots or accessibility audits. Future intentional color/icon/spacing changes require review, updates to both the component-owned guide and test, and real device snapshots.
- Run `node --test CustomDrive/tests/test_ui_style_tokens_r45.cjs`, then existing R33/R35/R36/R43/R44 suites and Python tests. Verify both apps at 390/768/1024/desktop: no lost overrides after refresh, manual pad/STOP, operator feedback for Apply/Save, Mission 1 timeline state, 100/50/0 Grip and Drop-off positions, servo role actions, keyboard focus, zero-threshold gate and responsive layout.
- Do not merge R45 before R44/R43/R36/R35/R33 or without explicit approval. No PR merge was attempted.
