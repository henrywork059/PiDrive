# PATCH NOTES — piTrainer_0_6_5 Colour System and Slim Splitter Patch

## Request summary
- Review all use of colour and improve the presentation by applying clearer colour roles.
- Research current UI colour/contrast and Qt styling guidance before patching.
- Reduce the thickness of the visible sliding/splitter bar by about 50%.

## Cause / root cause
The V6.4 UI already had a central formatting system, but colour use was still spread across `styles.py` and several plotting/overlay modules as local hex values. This made future visual tuning harder and allowed similar colours to drift between widgets, tables, buttons, plots, and overlay text.

The screenshot also showed the centre splitter/slider handle visually dominating narrow panels. The handle was useful for resizing, but it was too thick and too bright relative to the surrounding content.

## Research applied
- Used current UI accessibility guidance to keep text/background contrast high and to avoid relying on colour alone for meaning.
- Used a semantic role approach similar to modern design systems: neutral dark surfaces, blue/cyan for navigation/focus, green for guided forward action, yellow amber for browsing/location picking, and red/pink for destructive/error actions.
- Used Qt stylesheet guidance for scrollbars/splitter handles: thickness belongs in central width/height values and handle styling should be controlled from the shared stylesheet.

## Files changed
- `piTrainer/piTrainer/ui/theme.py`
  - New central semantic colour token module.
  - Adds `THEME_COLORS` and `theme_color()` so Qt styles and matplotlib plots share one palette.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_5_color_system_slim_splitters`.
  - Adds theme colour tokens to stylesheet replacement values.
  - Reduces scrollbar thickness from `10/11/12` to `5/6/6` across compact/comfortable/spacious density profiles.
  - Reduces splitter handle width from `9/10/11` to `5/5/6` across compact/comfortable/spacious density profiles.
- `piTrainer/piTrainer/ui/styles.py`
  - Reworks the Qt stylesheet to use semantic colour tokens rather than hard-coded local hex values.
  - Improves action colour separation:
    - green for main guided actions;
    - blue for primary navigation/focus;
    - cyan for active focus, panel accents, and checkbox/session selection emphasis;
    - yellow-forward amber for Browse/location buttons;
    - red/pink for destructive actions.
  - Makes splitter handles and scrollbars slimmer and less visually heavy.
  - Gives splitter panel titles a subtle cyan left accent instead of competing thick blue blocks.
- `piTrainer/piTrainer/panels/data/data_plot_panel.py`
  - Uses the shared plot background colour token.
- `piTrainer/piTrainer/services/data/plot_service.py`
  - Uses shared theme colours for data plots.
  - Adds distinct steering/speed colours in timelines, histograms, scatter plots, and legends.
- `piTrainer/piTrainer/panels/train/train_history_panel.py`
  - Uses shared plot colours and a central plot colour cycle for training curves.
- `piTrainer/piTrainer/panels/validation/validation_plot_panel.py`
  - Uses the shared plot background colour token.
- `piTrainer/piTrainer/services/validation/validation_service.py`
  - Uses shared theme colours for validation scatter, histogram, trace, reference line, grid, labels, and legends.
- `piTrainer/piTrainer/services/data/overlay_service.py`
  - Replaces local overlay text hex colour with the shared text colour token while preserving existing overlay path colours and metadata behaviour.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.5` / `piTrainer_0_6_5`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the new `theme.py` colour source of truth.
  - Documents the slimmer splitter/scrollbar rule.
  - Updates colour-role guidance.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions for the central colour system, yellow-forward amber Browse buttons, and slimmer splitters/scrollbars.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_5.md`
  - This patch note.

## Exact behaviour changed
- The visible app version now reports `0.6.5`.
- Scrollbars are slimmer in all density profiles.
- Splitter handles are roughly half the previous thickness.
- Browse/location buttons remain amber but are now more yellow and less brown.
- Main green action buttons, blue primary actions, danger buttons, selected rows, checkboxes, tabs, panel headers, and hints now follow a central semantic palette.
- Data, training, and validation plots use the same dark plot surface and role colours as the app UI.
- Steering and speed plots are easier to distinguish by colour.
- The stylesheet no longer carries many unrelated hard-coded hex colours; the palette lives in `theme.py`.

## Behaviour intentionally not changed
- Data Workflow remains ordered as `1 Load`, `2 Manage`, `3 Review`.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot`.
- Frame Filter remains in `2 Manage`.
- Merge Sessions remains in `3 Review` and collapsed by default.
- Data Control remains expanded by default.
- Batch frame deletion and the Data Control delete confirmation checkbox remain unchanged.
- `frame_id` remains the first Record Preview column.
- The Record Preview first-column anchoring from V6.4 remains unchanged.
- Playback controls remain directly under the image preview.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and overlay metadata support are unchanged.
- Preprocess, Train, Validate, and Export runtime logic is unchanged apart from plot presentation colours.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + 0.6.1 + 0.6.2 + 0.6.3 + 0.6.4 install.
- `FORMAT_VERSION` was bumped so old saved visual layout state is less likely to preserve the previous handle/scrollbar presentation.
- `theme.py` is a new shared UI module; future code should import `theme_color()` instead of adding local hex values.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1`, `0_6_2`, `0_6_3`, and `0_6_4` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_4.md`
  - `PATCH_NOTES_piTrainer_0_6_3.md`
  - `PATCH_NOTES_piTrainer_0_6_2.md`
  - `PATCH_NOTES_piTrainer_0_6_1.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support.
  - PiSD V7 overlay redraw support.
  - Preprocessing/manual-drive fixes.
  - Training-start preflight fixes.
  - Full-width splitter layout.
  - Horizontal overflow scroll behaviour.
  - V6.1 playback-under-preview layout.
  - V6.2 Data Workflow and Data Review tab orders.
  - V6.2 AI-agent instruction document.
  - V6.3 Data Control delete checkbox.
  - V6.3 multi-row selection and batch delete support.
  - V6.3 `frame_id` first-column order.
  - V6.4 first-column anchoring.
  - V6.4 removal of `Next Step:` and `Show:` visible label prefixes.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip`, `piTrainer_0_6_2_patch.zip`, `piTrainer_0_6_3_patch.zip`, and `piTrainer_0_6_4_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the Data page/style files, current style guide, agent instructions, and latest patch notes.
- Performed web research on colour contrast, semantic UI colour systems, and Qt scrollbar styling before editing.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.5`.
  - `PATCH_VERSION` reports `piTrainer_0_6_5`.
  - `FORMAT_VERSION` reports `0_6_5_color_system_slim_splitters`.
  - stylesheet colour placeholders all match central theme tokens.
  - no remaining local six-digit hex colours exist in Python source outside `theme.py`.
  - compact/comfortable/spacious splitter and scrollbar values are reduced from V6.4.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4 to identify only intended changed/new files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch changes UI colours, plot colours, and splitter/scrollbar presentation only.

## Known limits / next steps
- Plot colours are now centralised, but users may still prefer different colour semantics after seeing the live GUI on their monitor. Future tuning should edit `theme.py` first.
- The splitter handle is thinner by request; if it becomes too difficult to grab on a small touchscreen, a later patch can add a larger invisible grab margin while keeping the visible handle slim.
