# PATCH NOTES — piTrainer_0_5_5 Compact Guided Banner Patch

## Request summary
- Make the top page banner more compact vertically.
- Replace the large green next-step information box with a compact green button.
- When the banner next-step button is clicked, it should guide the user to the real green action button instead of merely displaying text.
- Preserve V5.0–V5.4 behaviour, including full-width splitters, horizontal overflow scrolling, unified formatting, PiSD V7 data, and overlay support.

## Cause / root cause
V5.4 fixed panel overflow by adding scrollable panel bodies, but the page banner still used a full instruction card on the right side. On shorter screens this consumed too much vertical space before the real workspace began. The green banner card also described the next action, but it did not direct the user to the actual action button inside the workflow panel.

## Files changed
- `piTrainer/piTrainer/ui/formatting.py`
  - Bumps the layout version to `0_5_5_compact_guided_banner`.
  - Adds central compact banner margins and spacing values to the density profiles.
- `piTrainer/piTrainer/ui/layout_widgets.py`
  - Makes `make_page_banner()` build a compact one-line-summary banner.
  - Replaces the right-side green label with a green button.
  - Allows the banner button to call a page-specific reveal callback.
- `piTrainer/piTrainer/ui/styles.py`
  - Reduces page-banner visual bulk.
  - Adds styling for the compact green banner next-step button.
  - Adds spotlight styling for the real green Next Step button when the banner guides the user to it.
- `piTrainer/piTrainer/pages/dock_page.py`
  - Adds `reveal_widget()` helper.
  - The helper activates the correct workflow tab, expands any collapsed section ancestor, scrolls the target into view, focuses it, and briefly highlights it.
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
  - Replaces long banner next-step text with compact `Show: ...` banner buttons connected to the real workflow action.
- `piTrainer/piTrainer/panels/data/session_source_panel.py`
  - Keeps the Load Selected button as `self.load_btn` so the banner can reveal it.
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
  - Keeps the Confirm and Start Preprocess button as `self.apply_btn` so the banner can reveal it.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.5.5` / `piTrainer_0_5_5`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_5_5.md`
  - This patch note.

## Exact behaviour changed
- The top banner uses smaller vertical margins and a single-line summary.
- The large green next-step information box is replaced by a compact green button.
- The banner button no longer performs the workflow action directly. It guides the user to the real green Next Step action button.
- Clicking the banner button now:
  - switches to the correct workflow sub-tab if needed;
  - expands the relevant collapsible section if needed;
  - scrolls the real action button into view;
  - focuses it;
  - briefly highlights it with a brighter border/background;
  - writes a short status message.
- Banner buttons are now:
  - `Show: Load Selected`
  - `Show: Confirm Preprocess`
  - `Show: Start Training`
  - `Show: Run Validation`
  - `Show: Export Artifacts`
- The app window/status version now reports `0.5.5`.

## Preserved behaviour
- V5.4 horizontal overflow scrolling inside reduced splitter panels is preserved.
- V5.3 visible version infrastructure is preserved and updated.
- V5.2 unified formatting remains the central style system.
- V5.1 responsive splitter behaviour is preserved.
- Full-width splitter workspaces are preserved.
- Green, wide, subtle-pulse real Next Step buttons are preserved.
- PiSD V7 `labels.jsonl` / `records.jsonl` support is preserved.
- PiSD V7 overlay redraw is preserved.
- Preprocessing/manual-drive fixes are preserved.
- Training-start checks are preserved.
- Data loading, validation, and export logic are not changed.

## Rollback-risk check
- Checked the latest V5.4 code state before patching.
- Checked the latest patch notes `0_5_4`, `0_5_3`, and `0_5_2` before patching.
- This patch only changes presentation guidance, banner layout, target reveal helpers, and visible version metadata.
- It does not restore older dock layouts.
- It does not remove overflow scrolling, unified formatting, splitters, V7 data loading, V7 overlays, preprocessing fixes, or training-start fixes.

## Verification actually performed
- Built forward from the V5.4 working state.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Checked changed files to confirm the patch is presentation/guidance focused plus this patch note.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Full TensorFlow training was not run because this patch changes presentation guidance only.

## Known limits / next steps
- The compact banner summary is intentionally one line. If the window is very narrow, read the full next-step instruction from the banner button tooltip or the workflow panel intro.
- The banner button guides to the actual action button; it does not click the action for the user, to avoid accidental data loading, preprocessing, training, validation, or export.
