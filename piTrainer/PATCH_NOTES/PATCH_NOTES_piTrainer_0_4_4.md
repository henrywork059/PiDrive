# PATCH NOTES — piTrainer_0_4_4

## Request summary
- Fix the startup crash reported after pulling/applying `piTrainer_0_4_3`.
- Preserve the whole-program readability/layout improvements from `0_4_3` and the PiSD V7 data/overlay support from `0_4_0`.

## Cause / root cause
- `piTrainer_0_4_3` introduced a small typo in `ExportOptionsPanel` while standardising form layout helpers.
- The code called `destination_standardize_form_layout(form)`, but no function with that name exists and the local variable is `destination_form`.
- Because the Export page is created during `MainWindow` startup, the typo caused the whole application to fail before the window opened.

## Files changed
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_4.md`

## Exact behaviour changed
- Replaced the invalid call:
  - `destination_standardize_form_layout(form)`
- With the correct helper call:
  - `standardize_form_layout(destination_form)`
- The Export Options destination form still uses the same `0_4_3` standardised layout style.
- No panel layout, PiSD V7 loader, overlay renderer, training, validation, or export workflow behaviour was otherwise changed.

## Rollback-risk check
- Checked latest patch note `0_4_3` and the previous three piTrainer V4 notes: `0_4_2`, `0_4_1`, and `0_4_0`.
- This patch only changes the one typo in the Export Options panel and adds this patch note.
- The `0_4_3` guided readability redesign remains intact.
- The `0_4_2` tabbed/collapsible workflow redesign remains intact.
- The `0_4_1` scrollable workflow sidebar redesign remains intact.
- The `0_4_0` PiSD V7 `labels.jsonl` / overlay redraw support remains intact.

## Verification actually performed
- Applied patches forward through `piTrainer_0_4_3` in a clean working folder.
- Searched for the invalid helper name and confirmed the reported typo was removed.
- Parsed all Python files with `ast.parse` to check for syntax validity.
- Ran `python3 -m compileall -q piTrainer` successfully in the sandbox.
- Checked the patch zip contents to ensure it contains only the changed file and patch notes under the correct `piTrainer/...` structure.

## Verification not performed
- A real PySide6 GUI launch could not be run inside this sandbox because the GUI dependency/runtime is not available here.
- The user's local Windows environment should now be able to launch because the reported startup `NameError` is fixed before the Export page finishes constructing.

## Known limits / next steps
- If another runtime error appears after this fix, report the new traceback so it can be patched forward without rolling back the UI improvements.
