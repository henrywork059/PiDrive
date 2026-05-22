# PATCH NOTES — piTrainer_0_5_7 Format and Style Guide Patch

## Request summary
- Add a format/style instruction document that records the presentation and styling decisions for the trainer.
- Keep the current patch-only delivery style.
- Keep the visible app version current.
- Preserve the V5.6 Data Review tabs and all accepted V5 functionality.

## Cause / root cause
The trainer now has a central formatting system and several accepted layout decisions: full-width splitters, compact banners, green Next Step buttons, scrollable panel bodies, workflow tabs, and responsive density profiles. These decisions were implemented in code, but there was not yet a human-readable guide explaining which styling decisions should be preserved and where future changes should be made. Without a guide, future patches could accidentally reintroduce one-off styling, cramped dock stacks, or inconsistent panel behaviour.

## Files changed
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - New documentation file describing the current trainer UI format rules and styling decisions.
  - Documents the central formatting source, stylesheet source, splitter layout principle, scroll behaviour, banners, workflow tabs, collapsible sections, Next Step buttons, tables, forms, density profiles, colour roles, version display, and future patch guidance.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.5.7` / `piTrainer_0_5_7`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_5_7.md`
  - This patch note.

## Exact behaviour changed
- The application window/status version now reports `0.5.7`.
- A new style instruction document is included with the trainer at:
  - `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`

## Behaviour not changed
- No page layout, panel layout, data loading, preprocessing, training, validation, export, or overlay logic was changed in this patch.
- No old layout behaviour was restored.
- No config or runtime data was reset.

## Preserved behaviour
- V5.6 combined Data Review tabs are preserved:
  - `1 Records`
  - `2 Plot`
- V5.5 compact guided banner and `Show: ...` reveal buttons are preserved.
- V5.4 horizontal/vertical overflow scrolling inside reduced panels is preserved.
- V5.3 visible version infrastructure is preserved and updated.
- V5.2 unified central formatting remains active.
- V5.1 responsive splitter behaviour is preserved.
- Full-width splitter workspaces are preserved.
- Green, wide, subtle-pulse real Next Step buttons are preserved.
- PiSD V7 `labels.jsonl` / `records.jsonl` support is preserved.
- PiSD V7 overlay redraw is preserved.
- Preprocessing/manual-drive fixes are preserved.
- Training-start checks are preserved.

## Rollback-risk check
- Checked the latest V5.6 code state before patching.
- Checked the latest patch notes `0_5_6`, `0_5_5`, and `0_5_4` before patching.
- This patch only adds documentation and updates visible version metadata.
- It does not change the Data page V5.6 Records/Plot tab structure.
- It does not remove overflow scrolling, unified formatting, splitters, guided banner behaviour, V7 data loading, V7 overlays, preprocessing fixes, or training-start fixes.

## Verification actually performed
- Built forward from the V5.6 working state.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Confirmed the new documentation file is included in the patch path:
  - `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox because this patch does not change UI rendering code.
- Full TensorFlow training was not run because this patch is documentation/version-only.

## Known limits / next steps
- The guide documents the current V5 design direction. Future visual changes should update the guide when they intentionally change the format rules.
- If the user later wants an in-app Help/About dialog for this guide, it can be linked from the F1 shortcuts dialog or an About menu.
