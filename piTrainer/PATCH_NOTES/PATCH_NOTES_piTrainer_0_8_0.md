# PATCH NOTES — piTrainer_0_8_0 V8 Stable Baseline Package

## Request summary
- Pack the current accepted piTrainer work as V8.
- Also provide a patch-only `0_8_0` package so an existing `0.7.3` install can be promoted to the V8 version line without copying a full project package.

## Cause / root cause
- The V7 patch line has accumulated accepted changes through `piTrainer_0_7_3`:
  - V7.1 strengthened horizontal-flip label safety across preprocessing, training, validation, and review display.
  - V7.2 hid generated/preprocessed rows from the default Data Review list while preserving them for training and validation, and redirected synthetic-row edit actions to the original source frame.
  - V7.3 added the startup version access manifest gate.
- A new full baseline lets future work build forward from a clean V8 package instead of replaying V7 plus multiple patches.

## Files changed
- `piTrainer/piTrainer/version.py`
  - Promotes visible app version to `0.8.0` / `piTrainer_0_8_0`.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_8_0_stable_v8_baseline`.
- `piTrainer/AGENTS.md`
  - Updates the AI-agent baseline/version guidance from V7 / `0_7_x` to V8 / `0_8_x`.
  - Adds the V8 stable baseline rule and reminds future agents not to roll back V7.1, V7.2, or V7.3 accepted changes.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Updates the style guide to describe V8 as the current stable baseline.
  - Adds a V8 version-gate reminder: the online manifest must allow `0.8.0` before V8 can open with the gate enabled.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_0.md`
  - This patch note.

## Exact behaviour changed
- The app title/status/version now reports:
  - `0.8.0`
  - `piTrainer_0_8_0`
- Future AI-agent guidance now treats `piTrainer_0_8_0` as the latest accepted full baseline.
- Future patch naming guidance now continues as:
  - `piTrainer_0_8_1_patch.zip`
  - `piTrainer_0_8_2_patch.zip`
  - and so on.

## Behaviour intentionally not changed
- No runtime logic, model architecture, preprocessing algorithm, training settings, validation logic, export format, or version-gate algorithm was intentionally changed in this promotion patch.
- The full V8 package preserves accepted behaviour from V7 plus patches `0_7_1` through `0_7_3`, including:
  - horizontal-flip image/label safety: flipped images use inverted steering and unchanged speed/throttle;
  - generated/preprocessed rows use `s_` frame IDs and trace metadata;
  - generated rows are hidden from the default Data Review table while remaining available for Train and Validate;
  - Validation `Edit in Data` redirects generated rows to their original source frame where possible;
  - startup version access manifest gate with `enabled=true`, `fail_closed=true`, timeout, and cache;
  - all V7 baseline behaviours inherited from accepted V6 work, including PiSD V7 data/overlay support, three-column Train/Validate layouts, Record Preview sorting, soft-hide deletion, bulk edit optimisations, Auto Preprocess horizontal flip defaults, random-row split default, 100 default epochs, and export log clarity.

## Compatibility notes
- `piTrainer_0_8_0.zip` is a full V8 package and can be used as a new baseline install.
- `piTrainer_0_8_0_patch.zip` is a patch-only promotion package intended for an install that already has full V7 plus accepted patches through `piTrainer_0_7_3` applied.
- If starting from fresh `piTrainer_0_7_0`, either use the full V8 zip or apply accepted patches `0_7_1` through `0_7_3` before applying the `0_8_0` patch.
- The local version gate config remains enabled and fail-closed. Before running/distributing V8, the online manifest at the configured URL must allow `0.8.0`; otherwise V8 will correctly refuse to open.
- At packaging time, the checked online manifest still allowed `0.7.3`. Update `release_control/pitrainer_access.json` in GitHub before using the V8 build as a controlled release.

## Rollback-risk check
- Built forward from full `piTrainer_0_7_0` V7 baseline plus accepted patches:
  - `piTrainer_0_7_1_patch.zip`
  - `piTrainer_0_7_2_patch.zip`
  - `piTrainer_0_7_3_patch.zip`
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous three relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_7_3.md`
  - `PATCH_NOTES_piTrainer_0_7_2.md`
  - `PATCH_NOTES_piTrainer_0_7_1.md`
  - `PATCH_NOTES_piTrainer_0_7_0.md`
- Confirmed this promotion patch does not intentionally roll back:
  - V7.3 startup manifest gate;
  - V7.2 generated-data hiding and edit redirection;
  - V7.1 horizontal-flip label safety and flipped preview/review display;
  - V7 stable baseline behaviour inherited from V6.20.

## Verification actually performed
- Applied `piTrainer_0_7_1_patch.zip`, `piTrainer_0_7_2_patch.zip`, and `piTrainer_0_7_3_patch.zip` over a fresh `piTrainer_0_7_0` tree.
- Inspected the latest code tree, latest patch note, and previous three piTrainer patch notes.
- Confirmed the real entry point remains:
  - `piTrainer/main.py`
- Opened the configured online manifest URL and confirmed it still allowed `0.7.3` at packaging time, so the manifest must be updated for V8.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Static-checked that:
  - `APP_VERSION` reports `0.8.0`;
  - `PATCH_VERSION` reports `piTrainer_0_8_0`;
  - `FORMAT_VERSION` reports `0_8_0_stable_v8_baseline`;
  - `AGENTS.md` names V8 / `0_8_x` as the future baseline/version line;
  - the V8 patch-only package contains only the promotion files and this patch note.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation/export was not run.
- Real PyInstaller `.exe` packaging with the version gate config bundled was not tested.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- V8 is a packaging/promotion baseline. Functional changes after V8 should continue as `0_8_x` patches.
- Update the online release-control manifest before testing V8 startup with `fail_closed=true`. Suggested V8 manifest shape:

```json
{
  "app": "PiTrainer",
  "latest": "0.8.0",
  "allowed_versions": ["0.8.0"],
  "blocked_versions": ["0.7.0", "0.7.1", "0.7.2", "0.7.3"],
  "message": "This PiTrainer version is no longer enabled. Please update to the latest version.",
  "support_message": "Please contact the project owner for the newest PiTrainer build."
}
```
