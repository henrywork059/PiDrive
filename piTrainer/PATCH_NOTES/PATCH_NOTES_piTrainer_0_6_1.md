# PATCH NOTES — piTrainer_0_6_1 Data Page Layout Optimisation Patch

## Request summary
- Move playback controls so they sit directly underneath the image preview.
- Move dataset statistics into the central Data Review area.
- Remove the separate Data Actions panel from the active Data page layout.
- Keep each action button close to the panel it belongs to instead of collecting unrelated duplicated buttons in one generic panel.

## Cause / root cause
In V6, the Data page had the correct full-width splitter layout, but some controls were still grouped by older panel habits rather than by task ownership:

- `Playback Control` was inside the left workflow Review tab, away from the image being played.
- `Dataset Stats` was inside the Load workflow even though it describes the loaded/reviewed dataset.
- `Data Actions` duplicated controls that already existed in better locations, especially refresh/load in `Session Source` and clear filter in `Frame Filter`.

This made the Data page busier than needed and increased the chance of users clicking duplicate controls in different places.

## Files changed
- `piTrainer/piTrainer/pages/data_page.py`
  - Removes `DataActionsPanel` from the active Data page layout.
  - Keeps the Load workflow focused on `Session Source` only.
  - Keeps the Review workflow focused on `Frame Filter` and `Overlay Controls` only.
  - Moves dataset stats into the central `Data Review` tabs.
  - Changes `Data Review` tabs to `1 Stats`, `2 Records`, `3 Plot`.
  - Builds a right-side visual stack containing image preview first and playback controls directly underneath.
  - Renames the right splitter panel to `Image Preview + Playback + V7 Overlay`.
- `piTrainer/piTrainer/panels/data/playback_control_panel.py`
  - Makes the playback helper text shorter for the new location under the image preview.
  - Initializes the playback buttons to the stopped state.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_1_data_review_playback_cleanup` so older saved splitter/tab layout state does not override the new default arrangement.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.6.1` / `piTrainer_0_6_1`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Updates the documented V6 Data page structure.
  - Records that stats belong in `Data Review`, playback belongs under image preview, and generic Data Actions should not be reintroduced.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_1.md`
  - This patch note.

## Exact behaviour changed
- The active Data page no longer shows a separate `Data Actions` collapsible section.
- Refresh remains available in `Data Workflow > 1 Load > Session Source`.
- Load Selected remains available as the green Next Step button in `Session Source`.
- Clear filter remains available in `Data Workflow > 2 Review > Frame Filter`.
- Dataset stats now appear in the centre `Data Review` panel as the `1 Stats` tab.
- Record rows are now in the `2 Records` tab.
- Plots are now in the `3 Plot` tab.
- Playback controls now sit directly below the image preview in the right visual panel.
- The right visual panel now combines image preview, playback, and V7 overlay review in one place.
- The app window/status version now reports `0.6.1`.

## Behaviour intentionally not changed
- `Session Source` refresh, browse, select all, clear selection, and green Load Selected behaviour are unchanged.
- `Frame Filter` apply/clear behaviour is unchanged.
- `Merge Sessions` and `Delete Selected Frame` remain in `Data Workflow > 3 Manage`.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and overlay metadata support are unchanged.
- Record table sorting, edit, delete, and merge services are unchanged.
- Preprocess, Train, Validate, and Export pages are unchanged.

## Compatibility notes
- This is a patch-only zip. It does not delete the old `data_actions_panel.py` file from an existing full install, because the normal patch install method overlays files rather than removing files.
- The old panel is no longer imported or added to the active Data page layout, so it should no longer appear in the UI after this patch is applied.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0`.
- Checked the latest V6 full-package note and previous patch notes:
  - `PATCH_NOTES_piTrainer_0_6_0.md`
  - `PATCH_NOTES_piTrainer_0_5_7.md`
  - `PATCH_NOTES_piTrainer_0_5_6.md`
  - `PATCH_NOTES_piTrainer_0_5_5.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support.
  - PiSD V7 overlay redraw support.
  - Preprocessing/manual-drive fixes.
  - Training-start preflight fixes.
  - Full-width splitter layout.
  - Horizontal overflow scroll behaviour.
  - Compact guided banner.
  - Green Next Step buttons.
  - Central formatting/style system.
  - V6 visible version infrastructure.

## Verification actually performed
- Inspected the real V6 entry point:
  - `piTrainer/main.py`
- Inspected latest and previous 3 relevant piTrainer patch notes before editing.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Checked source references to confirm `DataActionsPanel` is no longer imported or instantiated by `data_page.py`.
- Checked changed file list to keep the patch targeted to the Data page layout, playback panel helper text, formatting version, visible version, style guide, and this patch note.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Full TensorFlow training was not run because this patch only changes Data page presentation/layout.
- Real PiSD recording import was not re-run in this sandbox.

## Known limits / next steps
- Because this is an overlay patch, unused old files may remain on disk after install if they existed in the full V6 package. They are not active unless imported by future code.
- If a future patch adds a toolbar/menu system, the F1 shortcut list could be surfaced there instead of inside any data panel.
