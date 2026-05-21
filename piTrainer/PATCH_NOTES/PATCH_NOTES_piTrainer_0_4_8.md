# piTrainer 0_4_8 Patch Notes

## Request summary
- Make all workflow "Next Step" buttons green, subtly blinking, extended/full-width, and easy to find.
- Keep the 0_4_7 full-width splitter layout behavior.
- Adjust the default collapsed sections so only detailed settings and fine-detail data controls are collapsed by default.
- Preserve all previously accepted PiSD V7 data/overlay, training-start, layout, and bug-fix behavior.

## Cause / design issue
The 0_4_7 layout fixed the main width/proportion problem, but the forward workflow action on each page still looked similar to other primary blue buttons in some panels. Some important action panels were also collapsed by default, which made the next step harder to find. The user clarified that only detail settings and fine data details should be collapsed.

## Files changed
- `piTrainer/ui/layout_widgets.py`
  - Added `style_next_step_button()` helper.
  - The helper applies a consistent green "next step" role, full-width size policy, larger minimum height, pointer cursor, tooltip, and a slow subtle pulse timer.
- `piTrainer/ui/styles.py`
  - Added stylesheet rules for `QPushButton[role='nextStep']`.
  - Added a subtle alternate pulse state using the `pulse` property.
- `piTrainer/pages/data_page.py`
  - Kept Session Source, Dataset Stats, Data Actions, Playback Control, Merge Sessions, and Data Control visible by default.
  - Collapsed Frame Filter and Overlay Controls by default because they are fine-detail data review controls.
- `piTrainer/pages/preprocess_page.py`
  - Kept Source Summary and Preprocess Actions visible.
  - Collapsed Preprocess Filters and Preprocess Recipe by default because they are detailed configuration controls.
- `piTrainer/pages/train_page.py`
  - Kept Split Summary and Training Controls visible.
  - Collapsed Training Config by default because it is detailed configuration.
- `piTrainer/pages/validation_page.py`
  - Put Validation Actions before Validation Config so the run action is easier to find.
- `piTrainer/pages/export_page.py`
  - Put Export Actions before Export Options so the final action is easier to find.
- `piTrainer/panels/data/session_source_panel.py`
  - Converted `Load Selected` to a full-width green `Next Step: Load Selected` button.
  - Moved Select All / Clear into their own row above the next-step button.
- `piTrainer/panels/data/data_actions_panel.py`
  - Converted `Load Selected Sessions` to a green `Next Step: Load Selected Sessions` button.
- `piTrainer/panels/preprocess/preprocess_actions_panel.py`
  - Converted `Confirm and Start Preprocess` to a green `Next Step: Confirm and Start Preprocess` button.
- `piTrainer/panels/train/train_control_panel.py`
  - Converted `Start Training` to a green full-width `Next Step: Start Training` button.
  - Moved it to its own row so it is not squeezed beside Prepare/Stop.
- `piTrainer/panels/validation/validation_actions_panel.py`
  - Converted `Run Validation` to a green `Next Step: Run Validation` button.
- `piTrainer/panels/export/export_actions_panel.py`
  - Converted `Export Selected Artifacts` to a green `Next Step: Export Selected Artifacts` button.

## Exact behavior changed
- Every main forward action in the workflow is now green and visually distinct from secondary actions.
- The next-step buttons are full-width or given expanding width so they are easier to locate.
- The pulse is deliberately slow and subtle; it changes the green shade/border rather than flashing aggressively.
- Main action panels are open by default.
- Detail settings / fine data tools are the main areas collapsed by default:
  - Data Frame Filter
  - Data Overlay Controls
  - Preprocess Filters
  - Preprocess Recipe
  - Training Config
  - existing internal fine-detail sections such as plot controls, image edit controls, validation frame filter, and advanced train/preprocess subsections

## Verification performed
- Applied on top of the accepted `piTrainer_0_4_7` state.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Checked that changed files are limited to page layout defaults, button presentation, and reusable UI styling/helper code.
- Checked that no PiSD V7 labels/records loading, overlay redraw, training-start preflight, sorted edit/delete, or full-width splitter logic was removed.

## Known limits / next steps
- The sandbox does not have a real Windows/PySide display session, so the pulse animation was validated by code compilation and Qt API usage rather than a live visual render.
- If the pulse feels too strong or too weak in the real app, adjust the two green colors in `piTrainer/ui/styles.py` or the timer interval in `style_next_step_button()`.
