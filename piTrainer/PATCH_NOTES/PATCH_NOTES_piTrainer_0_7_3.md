# PATCH NOTES — piTrainer_0_7_3 Startup Version Access Manifest Patch

## Request summary
- Add a small safety/access feature for packed PiTrainer releases.
- On app startup, check an online GitHub manifest before opening the main window.
- If the current app version is not allowed by the online manifest, show a clear message and close.
- Use the user's supplied manifest URL:
  - `https://raw.githubusercontent.com/henrywork059/PiDrive/refs/heads/main/release_control/pitrainer_access.json`

## Cause / root cause
- Packed `.exe` builds can continue to run after a newer PiTrainer release exists.
- The user wanted a simple way to discontinue access to a specific packed version by updating a small file online.
- A plain local password embedded in the app would be easy to copy or patch out, so this patch uses a version access manifest instead.

## Files changed
- `piTrainer/config/version_gate.json`
  - Adds local startup gate config.
  - Enables the gate for this release line.
  - Points at the GitHub raw manifest URL supplied by the user.
  - Uses a short startup timeout, fail-closed release behaviour, and a 12-hour cache.
- `piTrainer/piTrainer/security/__init__.py`
  - Adds the security helper package.
- `piTrainer/piTrainer/security/version_gate.py`
  - Adds the manifest/config/cache implementation.
  - Uses only Python standard-library networking and JSON parsing.
  - Checks `allowed_versions` and `blocked_versions` against the current app version.
  - Caches recent successful checks for temporary network failures.
- `piTrainer/piTrainer/app.py`
  - Runs the version gate after creating the QApplication and before creating/showing `MainWindow`.
  - Displays a blocking message box and exits if the current version is not allowed.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.7.3` / `piTrainer_0_7_3`.
- `piTrainer/AGENTS.md`
  - Adds V7.3 anti-rollback guidance for the startup manifest gate.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the manifest shape, startup behaviour, and PyInstaller packaging note for `config/version_gate.json`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_7_3.md`
  - This patch note.

## Exact behaviour changed
- PiTrainer now checks the configured online manifest before opening the main window when `enabled=true`.
- The supplied online manifest currently allows `0.7.3` and blocks `0.7.0`, `0.7.1`, and `0.7.2`.
- If `APP_VERSION` is listed in `blocked_versions`, PiTrainer shows the manifest message and closes.
- If `allowed_versions` is non-empty and `APP_VERSION` is not listed there, PiTrainer shows the manifest message and closes.
- If the online check succeeds and allows the version, PiTrainer opens normally and caches the successful manifest for the configured cache duration.
- If the online check fails and a fresh cache for the same app version exists, PiTrainer can open from cache.
- If the online check fails and no fresh cache exists, `fail_closed=true` makes PiTrainer refuse to open.

## Behaviour intentionally not changed
- This is a soft release-control gate, not strong anti-crack protection.
- No private token, GitHub credential, or real secret is stored in the app.
- Data loading, preprocessing, training, validation, export, synthetic row handling, flip label safety, and table behaviour are not intentionally changed.
- Generated/synthetic rows remain hidden in Data Review by default while still available for Train and Validate.
- Horizontal flip still inverts steering and preserves speed/throttle.
- The app still launches through the real entry point:
  - `piTrainer/main.py`

## Compatibility notes
- This is a patch-only zip intended for a V7 install with `piTrainer_0_7_1_patch.zip` and `piTrainer_0_7_2_patch.zip` already applied.
- The version gate config is enabled by default for this patch because the online manifest already allows `0.7.3`.
- For PyInstaller packaging, make sure `config/version_gate.json` is bundled or copied beside the executable. If it is not packaged and no external config is provided, frozen builds may fall back to default gate-disabled config.
- This feature needs internet access at least once per cache period when `fail_closed=true`.

## Rollback-risk check
- Built forward from full `piTrainer_0_7_0` V7 baseline plus accepted patches:
  - `piTrainer_0_7_1_patch.zip`
  - `piTrainer_0_7_2_patch.zip`
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous three relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_7_2.md`
  - `PATCH_NOTES_piTrainer_0_7_1.md`
  - `PATCH_NOTES_piTrainer_0_7_0.md`
  - `PATCH_NOTES_piTrainer_0_6_20.md`
- Confirmed this patch does not intentionally roll back:
  - V7.2 synthetic-data visibility and edit redirect;
  - V7.1 horizontal-flip label safety and review display fixes;
  - V7 stable baseline/version packaging rules;
  - V6.20 export log clarity;
  - V6.19 Validation three-column layout;
  - V6.18 Train three-column layout and synthetic `s_` IDs.

## Verification actually performed
- Opened the supplied manifest URL and confirmed it currently returns JSON allowing `0.7.3` and blocking `0.7.0`, `0.7.1`, and `0.7.2`.
- Inspected current `app.py`, `version.py`, latest patch notes, style guide, and AI-agent instructions before editing.
- Ran direct version-gate evaluation tests confirming:
  - `0.7.3` is allowed when listed in `allowed_versions`;
  - a missing version is blocked when `allowed_versions` is non-empty;
  - a version is blocked when listed in `blocked_versions`;
  - a manifest with the wrong `app` field is blocked.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Static-checked changed source files and version strings.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Full app startup with the real online check was not run in the sandbox Python environment.
- Real PyInstaller `.exe` packaging with the version gate config bundled was not tested.
- Full TensorFlow training/validation/export was not run.

## Known limits / next steps
- This is a soft lock. A technical user could still modify or patch a local copy.
- If `fail_closed=true`, users need internet access when no fresh cache exists.
- Future full release packages should include the version gate config and keep the online manifest aligned with `APP_VERSION`.
- For a future stronger design, the manifest could be signed and the app could verify the signature with a public key, but that was intentionally not added in this simple patch.
