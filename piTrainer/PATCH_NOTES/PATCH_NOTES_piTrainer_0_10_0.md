# PATCH NOTES — piTrainer_0_10_0 V10 Stable Baseline Promotion

## Request summary

Package the current uploaded piTrainer version as V10 and provide both:

- a full `piTrainer_0_10_0.zip` package;
- a patch-only `piTrainer_0_10_0_patch.zip` package.

The uploaded current component was inspected as `0.9.21 / piTrainer_0_9_21`, so this V10 package promotes that exact line forward rather than replacing it with an older baseline.

## Cause / reason

The current working piTrainer line has moved beyond the old V8 baseline guidance. The code and patch notes now extend through `piTrainer_0_9_21`, but the internal future-agent guidance and style guide still described V8 as the current full baseline.

A V10 stable promotion is needed so future patches can build from a clean `0_10_x` line without replaying or accidentally rolling back the accepted V9 updates.

## Files changed

- `piTrainer/piTrainer/version.py`
  - Updates visible app version from `0.9.21` to `0.10.0`.
  - Updates patch/version string from `piTrainer_0_9_21` to `piTrainer_0_10_0`.
- `piTrainer/AGENTS.md`
  - Updates the latest accepted full baseline from V8 to V10.
  - Updates future patch-only naming guidance to `piTrainer_0_10_x_patch.zip`.
  - Adds anti-rollback reminders for accepted V9 Data/overlay/refactor behaviour.
  - Updates version-gate guidance for the current `minimum_version` logic.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Updates the current style/baseline text from V8 to V10.
  - Records that V10 promotes the accepted V9 line through `0.9.21`.
  - Refreshes the version-gate manifest example for a controlled V10 release.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_10_0.md`
  - Adds this patch note.

## Exact behavior changed

- The app now reports:
  - `APP_VERSION = 0.10.0`
  - `PATCH_VERSION = piTrainer_0_10_0`
  - status text `Version 0.10.0 (piTrainer_0_10_0)`
- Future piTrainer patch guidance now points to the `0_10_x` line.
- Documentation now treats the accepted `0.9.21` state as the source for the V10 stable baseline.

## Behavior intentionally preserved

This promotion does not change:

- Data page workflow, table model, filtering, hiding/recovering, playback, bulk edit, or session loading.
- Preprocess horizontal flip behaviour, synthetic-row visibility, source-frame traceability, or hidden-row exclusion.
- Training, validation, export, and Export Validation logic.
- TFLite output parsing or validation.
- The V9 overlay work, including green path curves, default Speed bar and Steering arc visibility, responsive 30%-transparent overlay text, and the rule not to draw the same text several times.
- Packaging helper files and the real entry point `piTrainer/main.py`.
- Local version-gate config values in `piTrainer/config/version_gate.json`.

## Compatibility / migration notes

- The full V10 zip can be used as the new complete piTrainer package.
- The V10 patch zip is patch-only and is intended for an existing install already matching the uploaded `0.9.21` state.
- Because the local version gate remains enabled/fail-closed, the online manifest should be reviewed before distributing a controlled V10 release. The current version-gate code can allow newer versions through `minimum_version`; for a V10-only release, update the GitHub manifest `latest` and `minimum_version` to `0.10.0`.

## Rollback-risk check

Checked the latest current code state and the latest available patch notes:

- `PATCH_NOTES_piTrainer_0_9_21.md`
- `PATCH_NOTES_piTrainer_0_9_18.md`
- `PATCH_NOTES_piTrainer_0_9_17.md`
- `PATCH_NOTES_piTrainer_0_9_16.md`

The uploaded zip did not contain `PATCH_NOTES_piTrainer_0_9_19.md` or `PATCH_NOTES_piTrainer_0_9_20.md`, although `0.9.21` references them. This V10 promotion therefore checked the latest notes actually present in the uploaded package.

Confirmed this package only promotes version/baseline documentation and does not replace functional modules with older copies.

## Verification actually performed

- Inspected the uploaded `piTrainer.zip` file structure.
- Confirmed the real entry point remains `piTrainer/main.py`.
- Confirmed the uploaded active version file reported `0.9.21 / piTrainer_0_9_21` before editing.
- Inspected the latest and previous available piTrainer patch notes before patching.
- Checked the online version-gate manifest and confirmed it currently reports `latest: 0.9.0`, `minimum_version: 0.9.0`, and `allowed_versions: [0.9.0]`.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the updated version module imports and reports `0.10.0 / piTrainer_0_10_0`.
- Removed `__pycache__` folders before packaging.
- Prepared a full V10 zip with `piTrainer/` as the top-level folder.
- Prepared a patch-only V10 zip containing only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI startup/clicking was not run in this Linux sandbox because PySide6 is not installed here.
- Real training, validation, export, and TFLite checks were not run because this is a version/baseline promotion package.
- A PyInstaller / EXE rebuild was not run.
- The online GitHub release-control manifest was checked but not modified from this component-only package.

## Known limits / next steps

- Push or update `release_control/pitrainer_access.json` in the GitHub repo if you want the public release-control file to display V10 as the latest controlled release.
- Rebuild the Windows one-folder EXE from this V10 source if you need a V10 executable package.
- Future bug-fix patches should continue as `piTrainer_0_10_1_patch.zip`, `piTrainer_0_10_2_patch.zip`, and so on unless a newer stable baseline is promoted.
