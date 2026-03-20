# CustomTrainer 0_1_13 — Patch Notes

## Patch summary

This patch focuses on page layout flexibility and faster validation review.

Main goals:
- replace the remaining rigid tab layouts with dockable panels that can be dragged, snapped, floated, and merged into tabs
- split each workflow page into smaller function-based panels
- add validation autoplay and stronger validation shortcuts for frame review
- keep the earlier 0_1_12 prediction-source fix intact

---

## Problems observed

### 1) Panels still felt fixed and could not really snap / merge
The previous UI used nested `QSplitter` layouts. Those splitters could resize sections, but they could not provide real dock-style behavior such as:
- dragging a panel to another edge of the page
- floating a panel
- tab-merging one panel with another
- restoring a more advanced docked layout per page

### 2) Some tabs still grouped too many tools into one large panel
The old layout made some pages harder to manage because a few large regions contained several unrelated functions.

### 3) Validation review still required manual frame stepping only
The Validation page already had a frame browser, but visual review of many predicted frames was still slower than needed.

### 4) Shortcuts were uneven across tabs
The app already had some Marking shortcuts, but the other pages needed better page-local actions, especially Validation.

---

## Root cause

The main limitation was architectural: page layouts were built from splitters rather than dock widgets. Splitters are fine for fixed resizing, but not for panel snapping, floating, or tab-merging.

Because of that:
- the UI could resize panels, but not reorganize them as real workspaces
- panel state persistence only remembered splitter sizes, not richer layout state
- Validation had browsing but not timed playback

---

## Attempted approach considered

### Keep extending the splitter system
I considered adding more nested splitters and more restore logic.

Why that was not enough:
- it would still not provide real snapping / floating / tab merging
- it would make page layouts more complex without solving the core issue
- it would still feel rigid when compared with true dockable panels

### Final direction chosen
Refactor the page shell to use an inner `QMainWindow` with `QDockWidget` panels per tab.

This gives:
- draggable panels
- snap docking
- floating panels
- tab merging
- saved dock state per page

---

## Final changes made

### A) New dockable workspace shell
Added a reusable dock-layout helper:
- `custom_trainer/ui/widgets/dock_workspace.py`

This new page shell:
- enables nested docks
- enables tabbed docks
- enables grouped dragging
- saves and restores dock layout state
- supports a reset-to-default panel layout action

### B) UI state storage upgraded
Updated:
- `custom_trainer/services/ui_state_service.py`

Changes:
- kept existing last-session-root persistence
- added saved dock-layout state storage in the local UI state JSON
- retained compatibility with earlier splitter-related state fields

### C) Marking page refactor
Updated:
- `custom_trainer/ui/pages/marking_page.py`

New functional panels:
- Session Source
- Sessions
- Images
- Image Preview (central)
- Classes
- Annotation Tools
- Current Item

New layout behavior:
- dock / float / tab-merge panel support
- reset panels button
- page-local shortcuts for scanning, loading last root, saving labels, frame stepping, and layout reset

### D) Training page refactor
Updated:
- `custom_trainer/ui/pages/train_page.py`

New functional panels:
- Training Config
- Actions
- Status
- Training Progress Plot (central)
- Training Preview
- Run Log
- Workflow Notes

New layout behavior:
- dock / float / tab-merge panel support
- reset panels button
- page-local shortcuts for start, stop, preview refresh, defaults fill, and layout reset

### E) Validation page refactor + autoplay
Updated:
- `custom_trainer/ui/pages/validate_page.py`

New functional panels:
- Validation / Prediction Config
- Prediction Overlay Settings
- Actions
- Status
- Validation Frame Preview (central)
- Predicted Frame Browser
- Run Log
- Validation Notes

New behavior:
- autoplay button for predicted frames
- adjustable autoplay interval in milliseconds
- stronger frame-review shortcuts
- autoplay stops safely when frames are cleared or source changes
- page panel reset support

Validation shortcuts added:
- `Ctrl+Enter` run prediction
- `Ctrl+Shift+Enter` run validation
- `Alt+Left / Alt+Right` previous / next predicted frame
- `Ctrl+Space` toggle autoplay
- `Esc` stop current task
- `Ctrl+Shift+0` reset validation panel layout

### F) Export page refactor
Updated:
- `custom_trainer/ui/pages/export_page.py`

New functional panels:
- Export Config
- Actions
- Status
- Run Log (central)
- Pi Export Notes

New behavior:
- dock / float / tab-merge panel support
- reset panels button
- page-local shortcuts for start, stop, defaults fill, and layout reset

### G) Main window shortcut/help update
Updated:
- `custom_trainer/ui/main_window.py`

Changes:
- version string moved to `0_1_13`
- F1 shortcut help now includes current-tab shortcut guidance
- startup still restores the last sessions root and page layout state

### H) README update
Updated:
- `CustomTrainer/README.md`

Changes:
- documents the new dockable panel workflow
- documents validation autoplay
- documents stronger shortcut coverage

---

## Files changed in this patch

- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_13.md`
- `CustomTrainer/custom_trainer/services/ui_state_service.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/custom_trainer/ui/pages/export_page.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/widgets/dock_workspace.py`

---

## Verification performed

### Code verification
Ran:
- `python -m compileall custom_trainer run_custom_trainer.py`

Result:
- patched files compile successfully

### Manual logic checks performed in code review
Checked that:
- every workflow page now uses a dockable workspace shell
- each page has a default panel layout and a reset path
- validation autoplay timer follows the chosen interval
- autoplay stops when predicted frames are cleared or replaced
- shortcut definitions are page-local so they are tied to the active page context
- startup restore still loads the last sessions root and then restores page layouts

---

## Notes / limitations

- I could compile the patched project here, but I could not fully launch the desktop GUI in this container because it does not provide a real interactive Windows/PySide desktop session.
- Docking behavior such as snapping feel and tab-merge interaction may still vary slightly by platform/window manager, but the implementation now uses Qt dock widgets rather than fixed splitters.

---

## Recommended user test steps

1. Replace the patched files.
2. Run `python run_custom_trainer.py`.
3. Open each tab and drag panel title bars to:
   - snap to a new side
   - float as a separate window
   - merge into tabs by dropping onto another dock title area
4. In Validation:
   - load weights
   - choose a prediction source
   - run prediction
   - step frames with `Alt+Left / Alt+Right`
   - toggle autoplay with `Ctrl+Space`
5. Press `F1` to confirm the shortcut help reflects the active tab.

---

## Suggested next follow-up if needed

If you want the next patch after this one, the most useful next refinement would be:
- add a visible “restore closed panels / panel list” menu per tab so hidden or floated panels can be recalled more explicitly
- persist autoplay speed in UI state
- add keyboard shortcuts for jumping by 10 frames in Validation
