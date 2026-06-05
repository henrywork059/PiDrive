# PATCH NOTES — piTrainer_0_9_0 Stable v9 Promotion + Version Gate Lock

## Request summary
- Promote the current working piTrainer line to v9.
- Disable all piTrainer versions lower than v9 through the online version-gate manifest.
- Keep the current reliable one-folder EXE packaging behavior that is now working.

## Cause / reason
- The current `0.8.15` packaging line is now confirmed working on the user's PC.
- The user requested this working line become v9.
- The existing version gate reads `release_control/pitrainer_access.json` from GitHub. In the current version-gate implementation, a non-empty `allowed_versions` list blocks every version not listed there.
- Therefore, setting `allowed_versions` to only `0.9.0` disables all lower version-gated builds such as `0.8.x`.

## Files changed
- `piTrainer/piTrainer/version.py`
  - Updates the app version from `0.8.15` to `0.9.0`.
  - Updates the patch/version string to `piTrainer_0_9_0`.
- `release_control/pitrainer_access.json`
  - Sets `latest` to `0.9.0`.
  - Adds `minimum_version` as `0.9.0` for clarity/future compatibility.
  - Sets `allowed_versions` to `["0.9.0"]` so all lower version-gated builds are rejected.
  - Updates the user-facing blocked-version message.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_0.md`
  - This patch note.

## Exact behavior changed
- The app now displays:
  - `0.9.0`
  - `piTrainer_0_9_0`
- The online access manifest now only allows:
  - `0.9.0`
- Lower version-gated builds such as `0.8.15`, `0.8.14`, `0.8.13`, and earlier `0.8.x` releases are rejected when they can reach the online manifest.
- The manifest message now tells users to update to v0.9.0 or later.

## Behavior intentionally not changed
- No UI layout was changed.
- No training, validation, export, TFLite, packaging, or data-loading code was changed.
- The current reliable PyInstaller one-folder packaging setup is preserved.
- The version-gate config path remains unchanged:
  - `piTrainer/config/version_gate.json`
- The release manifest remains in:
  - `release_control/pitrainer_access.json`

## Compatibility notes
- This is a patch-only v9 promotion package.
- Older builds that already include the version gate will be blocked by the non-empty `allowed_versions` list once they fetch the updated manifest.
- Very old builds that do not contain the version-gate feature cannot be blocked by this manifest because they do not check it.
- If a lower version is fully offline and still has a fresh cached allow result for the same app version, it may remain usable until that cache expires. Online lower versions should be blocked immediately after the manifest is updated on GitHub.
- Future v9 patch releases will need the manifest updated again, for example by adding `0.9.1` to `allowed_versions`, unless the version-gate code is later changed to enforce `minimum_version` directly.

## Rollback-risk check
- Built forward from the current GitHub piTrainer `0.8.15` state.
- Checked the latest and previous three relevant patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_8_15.md`
  - `PATCH_NOTES_piTrainer_0_8_14.md`
  - `PATCH_NOTES_piTrainer_0_8_13.md`
  - `PATCH_NOTES_piTrainer_0_8_12.md`
- Confirmed this patch does not intentionally roll back:
  - reliable packaging with no aggressive excludes from `0.8.15`;
  - training diagnostics from `0.8.14`;
  - frozen TensorFlow/Keras training packaging support from `0.8.13`;
  - unittest startup fix from `0.8.12`;
  - packaging zip retry from `0.8.11`;
  - entry-point path fix from `0.8.10`;
  - one-folder packaging helper from `0.8.9`;
  - earlier data, validation, export, and TFLite-output fixes.

## Verification actually performed
- Verified the version file parses with Python.
- Verified `release_control/pitrainer_access.json` is valid JSON.
- Verified the manifest allows `0.9.0`.
- Verified the manifest rejects lower sample versions using the existing `allowed_versions` rule:
  - `0.8.15`
  - `0.8.14`
  - `0.8.0`
- Confirmed the patch package contains only the v9 version file, the release-control manifest, and this patch note.

## Verification not performed
- Live Windows GUI launch was not run in this sandbox.
- A real online GitHub manifest fetch from the packaged app was not run in this sandbox.
- EXE rebuild was not run in this sandbox.

## Known limits / next steps
- Push this patch to GitHub, then run `git pull` on each PC.
- Rebuild the EXE from the v0.9.0 code.
- If future `0.9.x` releases should also open, update `release_control/pitrainer_access.json` to include those versions in `allowed_versions`.
