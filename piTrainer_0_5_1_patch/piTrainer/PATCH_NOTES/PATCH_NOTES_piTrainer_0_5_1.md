# PATCH NOTES — piTrainer_0_5_1 Responsive Presentation Full Package

## Request summary
- Build V5.1 forward from the accepted V5.0 full package.
- V5.1 must include all V5.0 updates, not replace them with an older state.
- Fix panels where content can become hidden or difficult to read when the window is smaller or splitters/scroll bars reduce the visible area.
- Improve panel, font, box, and splitter sizing so the UI adapts more cleanly to the current window size and pixel ratios.
- Research Qt layout behaviour and apply the improvement across the programme.

## Cause / root cause
The 0_5_0 presentation already used full-width splitters and scrollable workflow sidebars, but some widgets still had relatively large fixed/minimum heights and some splitter proportions were only initial sizes. On smaller windows, these minimums could force image, table, plot, or workflow content to be clipped or hidden behind scroll areas. The workflow sidebar also had a maximum width, which could make the left controls harder to read on larger screens while still crowding the content on smaller screens.

## Reference/design basis used
- Qt `QSplitter` supports user-controlled panel sizes and exposes pixel sizes through `sizes()` / `setSizes()`, so the fix keeps splitter-based workspaces but adds ratio-aware resizing.
- Qt `QSizePolicy` controls how widgets cooperate with the layout engine, so the patch reduces over-large hard minimums and uses expanding policies where the page should reflow.
- Qt `QScrollArea` can make oversized content reachable with scroll bars and can resize the child widget when `setWidgetResizable(True)` is used, so workflow controls remain scrollable but are no longer forced into a clipped narrow area.

## Files changed
- `piTrainer/main_window.py`
  - Reduced the hard minimum window size from `1100x720` to `960x620`.
  - Added width-aware UI density switching: compact, comfortable, and spacious.
  - Reapplies the stylesheet only when the window crosses density thresholds.
- `piTrainer/pages/dock_page.py`
  - Added `ResponsiveSplitter`, a ratio-aware splitter that preserves user splitter proportions while adapting to current pixel width/height.
  - Bumped layout version to `0_5_1_responsive_layout` so old cramped saved splitter states do not override the new defaults.
  - Reduced page shell and panel frame margins.
  - Removed the workflow panel maximum width and replaced it with softer minimums.
- `piTrainer/pages/data_page.py`
- `piTrainer/pages/preprocess_page.py`
- `piTrainer/pages/train_page.py`
- `piTrainer/pages/validation_page.py`
- `piTrainer/pages/export_page.py`
  - Added soft minimum pixel sizes for the main horizontal and vertical splitters.
  - Adjusted initial splitter proportions so workflow controls stay readable but do not consume too much space.
- `piTrainer/ui/layout_widgets.py`
  - Reduced page banner, collapsible section, form, and control-stack spacing.
  - Allowed horizontal scroll bars when needed in workflow scroll areas so wide controls are reachable instead of clipped.
  - Slightly reduced next-step button minimum height while preserving its green emphasis.
- `piTrainer/ui/styles.py`
  - Added density profiles for compact/comfortable/spacious font and widget metrics.
  - Made tab widths, input heights, button heights, scroll bar widths, and banner title size responsive through stylesheet variables.
  - Reduced excessive padding in group boxes, panel titles, helper cards, and tab controls.
- `piTrainer/panels/data/image_preview_panel.py`
  - Lowered the image preview hard minimum height.
  - Added resize-aware preview rendering so the image/overlay redraws to the actual available label size.
- `piTrainer/panels/validation/validation_frame_review_panel.py`
  - Lowered the validation preview hard minimum height.
  - Added resize-aware validation image/overlay rendering.
- `piTrainer/panels/data/session_source_panel.py`
  - Reduced the session list hard minimum height.
- `piTrainer/panels/data/preview_panel.py`
  - Reduced the record table hard minimum height.
- `piTrainer/panels/data/data_plot_panel.py`
  - Reduced the plot canvas hard minimum height.
- `piTrainer/panels/train/train_epoch_review_panel.py`
  - Reduced the epoch review image hard minimum height.
- `piTrainer/panels/validation/validation_plot_panel.py`
  - Reduced the validation plot canvas hard minimum height.

## Exact behaviour changed
- V5.1 is a full package containing the V5.0 state plus this patch.
- The main programme now adapts its visual density by window width:
  - compact below about 1180 px;
  - comfortable in normal desktop widths;
  - spacious above about 1680 px.
- Splitter sections now resize by stored ratios instead of only relying on one-time starting pixel sizes.
- User-dragged splitter proportions are preserved and then reapplied when the window is resized.
- Workflow panels no longer have a hard maximum width, so large monitors can give the left controls more readable space.
- Smaller windows should show more content before clipping because hard minimum heights were reduced.
- Preview images and validation overlay images use the current label size instead of fixed preview dimensions only.
- Scrollable workflow sidebars can expose a horizontal scroll bar if a wide field would otherwise be clipped.

## Preserved behaviour
- All V5.0 changes are preserved.
- PiSD V7 `labels.jsonl` / `records.jsonl` support is preserved.
- PiSD V7 overlay redraw is preserved.
- The preprocessing/manual-drive fix is preserved.
- The training-start fix is preserved.
- The green next-step buttons remain green, full-width, and easy to find.
- The full-width left/middle/right splitter workflow remains the main layout model.

## Rollback-risk check
- Checked the latest notes `0_5_0`, `0_4_10`, `0_4_9`, and `0_4_8` before patching.
- Confirmed the patch builds forward from the V5.0 full package.
- Did not restore older dock layouts.
- Did not remove green next-step buttons.
- Did not touch PiSD V7 data loading, preprocessing logic, training logic, validation logic, or export logic except for presentation-related sizing.

## Verification actually performed
- Built from `piTrainer_0_5_0_full.zip`.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Imported and generated compact, comfortable, spacious, and fallback stylesheets; confirmed stylesheet placeholders are fully replaced.
- Compared changed files against the V5.0 full package.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- A live Windows/PySide6 GUI render test was not run in this sandbox because PySide6 is not installed here.
- Full TensorFlow training was not run because this patch changes layout/presentation sizing only.

## Known limits / next steps
- If a specific panel still hides text at a very narrow width, report the page name and screenshot; the next patch can tune that panel’s minimums or make that specific section use a different layout.
- If the compact font feels too small on your monitor, increase the compact `base_font` value in `piTrainer/ui/styles.py` from `12` to `13`.
