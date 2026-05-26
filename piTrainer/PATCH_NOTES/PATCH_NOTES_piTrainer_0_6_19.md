# PATCH NOTES — piTrainer_0_6_19 Validation Three-Column Layout Patch

## Request summary
- Change the Validate tab to a three-column layout.

## Cause / root cause
- After V6.18 moved the Train tab to a clearer three-column workspace, the Validation page still used a two-column layout with the frame review stacked vertically above the plot/log area.
- That made validation review less consistent with Train and could force either the frame preview or the plot/log region to be shorter than needed.

## Files changed
- `piTrainer/piTrainer/pages/validation_page.py`
  - Replaces the old two-column layout plus nested right vertical splitter with a direct three-column horizontal workspace.
  - Keeps `Validation Workflow` on the left.
  - Keeps `Validation Plot / Log` in the middle.
  - Moves `Validation Frame Review` to the right column.
  - Adds numbered result tabs: `1 Plot` and `2 Log`.
- `piTrainer/piTrainer/ui/formatting.py`
  - Adds a central `validation_three_panel_workspace` splitter preset.
  - Updates `FORMAT_VERSION` to `0_6_19_validation_three_columns` so saved layouts do not force the old two-column validation layout.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.19` / `piTrainer_0_6_19`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the accepted Validation page three-column layout.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve the Validation page three-column layout.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_19.md`
  - This patch note.

## Exact behaviour changed
- The Validation page now opens as:

```text
[Validation Workflow] | [Validation Plot / Log] | [Validation Frame Review]
```

- Frame review is no longer stacked above the plot/log area.
- Validation plots/logs and frame review now have separate side-by-side columns.
- The left workflow panel still contains:
  - `1 Run` with validation actions/config;
  - `2 Results` with the validation summary.
- The middle results panel now contains:
  - `1 Plot`;
  - `2 Log`.

## Behaviour intentionally not changed
- Validation still imports and uses `without_hidden_rows()` so hidden/soft-deleted rows are not validated.
- Validation still supports validating the current trained model or a saved `.keras` / `.h5` model.
- Validation still supports validation split, current filtered rows, and training split dataset sources.
- Validation frame review filtering, bad-threshold sorting, best/worst navigation, and `Edit in Data` behaviour are unchanged.
- Horizontal-flip validation image/label handling from V6.16 is unchanged.
- Train page three-column layout from V6.18 is unchanged.
- Preprocess defaults, synthetic `s_` IDs, random-row split, 100-epoch default, and soft-delete training exclusions are unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.18` install.
- Existing saved Validation page layouts may reset because `FORMAT_VERSION` changed. This is intentional so the new three-column layout is not overridden by an older saved two-column layout.
- No PiSD session data, preprocessing data, training split data, or saved model files are migrated or rewritten.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_18` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_18.md`
  - `PATCH_NOTES_piTrainer_0_6_17.md`
  - `PATCH_NOTES_piTrainer_0_6_16.md`
  - `PATCH_NOTES_piTrainer_0_6_15.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support;
  - PiSD V7 overlay redraw support;
  - preprocessing/manual-drive fixes;
  - training-start preflight fixes;
  - full-width splitter layout;
  - horizontal overflow scroll behaviour;
  - V6.1 playback-under-preview layout;
  - V6.2 Data Workflow and Data Review tab orders;
  - V6.2 AI-agent instruction document;
  - V6.3 Data Control checkbox and multi-row Record Preview selection;
  - V6.4 label cleanup and first-column anchoring intent;
  - V6.5 central theme token system;
  - V6.6 amber/green action colour semantics and centred steering slider;
  - V6.7 Bulk Edit Selected Frames panel and edit safety;
  - V6.8 traceable soft-delete / hidden-frame behaviour;
  - V6.9 fast batch JSONL bulk-edit path;
  - V6.10 Up/Down cycling, Bulk Edit Select All, and targeted edit optimisation;
  - V6.11 Preprocess auto workflow and training device/GPU controls;
  - V6.12 validation import fix, TensorFlow log handling, and queued edit responsiveness;
  - V6.13 simple model/view Record Preview table;
  - V6.14 sortable Record Preview with default `frame_id` sorting;
  - V6.15 default/auto horizontal flip preprocessing;
  - V6.16 horizontal-flip steering label guard;
  - V6.17 random-row training split and 100-epoch defaults;
  - V6.18 synthetic `s_` frame IDs and Train page three-column layout.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_18_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the current Validation page, Train page three-column reference layout, formatting presets, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.19`;
  - `PATCH_VERSION` reports `piTrainer_0_6_19`;
  - `FORMAT_VERSION` reports `0_6_19_validation_three_columns`;
  - Validation page uses `validation_three_panel_workspace`;
  - Validation page no longer builds the old nested `right_stack` splitter.
- Compared the working tree against fresh V6+0.6.1 through 0.6.18 to identify intended changed/new files only.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow validation/training was not run.
- Actual GPU hardware execution was not tested.

## Known limits / next steps
- The new Validation layout is compile/AST/static verified but should still be visually checked in the live Windows GUI.
- On very narrow screens, the three columns may need splitter adjustment by the user, but scrollbars should keep panel contents reachable.
