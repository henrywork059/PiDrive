# PATCH NOTES — piTrainer_0_7_0 V7 Stable Baseline Package

## Request summary
- Pack the current accepted piTrainer work as V7.
- Also provide a patch-only `0_7_0` package so an existing `0.6.20` install can be promoted to the V7 version line without copying a full project package.

## Cause / root cause
- The V6 patch line has accumulated accepted changes through `piTrainer_0_6_20`, including data layout, preprocessing, training, validation, export, table, style, soft-hide, and synthetic-data improvements.
- A new full baseline is useful so future work can build forward from a clean V7 package instead of replaying many `0_6_x` patches.

## Files changed
- `piTrainer/piTrainer/version.py`
  - Promotes visible app version to `0.7.0` / `piTrainer_0_7_0`.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_7_0_stable_v7_baseline`.
- `piTrainer/AGENTS.md`
  - Updates the AI-agent baseline/version guidance from V6 / `0_6_x` to V7 / `0_7_x`.
  - Keeps anti-rollback instructions for all accepted V6 features that are now part of V7.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Adds a V7 stable baseline note.
  - Updates wording so the guide describes the V7 trainer UI.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_7_0.md`
  - This patch note.

## Exact behaviour changed
- The app title/status/version now reports:
  - `0.7.0`
  - `piTrainer_0_7_0`
- Future AI-agent guidance now treats `piTrainer_0_7_0` as the latest accepted full baseline.
- Future patch naming guidance now continues as:
  - `piTrainer_0_7_1_patch.zip`
  - `piTrainer_0_7_2_patch.zip`
  - and so on.

## Behaviour intentionally not changed
- No runtime logic, model architecture, preprocessing algorithm, training settings, validation logic, or export format was intentionally changed in this promotion patch.
- The full V7 package preserves accepted behaviour from V6 plus patches `0_6_1` through `0_6_20`, including:
  - PiSD V7 `labels.jsonl` / `records.jsonl` support;
  - overlay redraw support;
  - full-width splitter layout;
  - playback controls under image preview;
  - Data Workflow order `1 Load`, `2 Manage`, `3 Review`;
  - Data Review order `1 Records`, `2 Stats`, `3 Plot`;
  - central style/theme system;
  - amber prerequisite buttons and green main-action buttons;
  - soft-hide deletion instead of physical frame deletion;
  - Record Preview model/view table with `frame_id` first, default `frame_id` sort, multi-select, and Up/Down cycling;
  - optimised single-frame and bulk edit paths;
  - one-click Auto Preprocess path with default horizontal flip augmentation;
  - horizontal-flip steering inversion and flip safety metadata;
  - synthetic `s_` frame IDs;
  - random-row default split and `100` default epochs;
  - Train page three-column layout;
  - Validation page three-column layout;
  - clearer export log and size-optimised TFLite float-I/O explanation.

## Compatibility notes
- `piTrainer_0_7_0.zip` is a full V7 package and can be used as a new baseline install.
- `piTrainer_0_7_0_patch.zip` is a patch-only promotion package intended for an install that already has V6 plus accepted patches through `piTrainer_0_6_20` applied.
- If starting from fresh `piTrainer_0_6_0`, either use the full V7 zip or apply all accepted `0_6_1` through `0_6_20` patches before applying the `0_7_0` patch.
- Existing PiSD recordings, preprocessed data, exported models, and runtime user data are not modified by this promotion patch.

## Rollback-risk check
- Built forward from fresh `piTrainer_0_6_0`.
- Applied accepted patches `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_20_patch.zip` before making the V7 promotion edits.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before finalising:
  - `PATCH_NOTES_piTrainer_0_6_20.md`
  - `PATCH_NOTES_piTrainer_0_6_19.md`
  - `PATCH_NOTES_piTrainer_0_6_18.md`
  - `PATCH_NOTES_piTrainer_0_6_17.md`
- Compared the V7 promotion tree against a fresh V6+0.6.1-through-0.6.20 reference tree to confirm the promotion patch only changes version/documentation/promotion-note files.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_20_patch.zip` over a fresh `piTrainer_0_6_0` tree.
- Inspected the latest code tree, latest patch note, and previous three piTrainer patch notes.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Static-checked that:
  - `APP_VERSION` reports `0.7.0`;
  - `PATCH_VERSION` reports `piTrainer_0_7_0`;
  - `FORMAT_VERSION` reports `0_7_0_stable_v7_baseline`;
  - `AGENTS.md` names V7 / `0_7_x` as the future baseline/version line;
  - the V7 patch-only package contains only the promotion files and this patch note.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training/validation/export was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- V7 is a packaging/promotion baseline. Functional changes after V7 should continue as `0_7_x` patches.
- If a user has only the original V6 full package without later `0_6_x` patches, they should install the full V7 package rather than only the V7 promotion patch.
