# piTrainer 0.11.36 — UI2 workflow readiness and native visual qualification (provisional)

Package baseline: 4d2f66aed73cc5a3ba59f94e0245afcd4fb41c6b

## Request and rationale
UI2-03/09/14: make the active stage's readiness visible without relying on icon color or tooltip discovery, while preserving the six existing tabs, layouts, keyboard shortcuts, selection semantics, data processing and performance optimizations. Build only on the exact green PR #93 trainer 0.11.35 source; this is a stacked draft, not an integration into main. Reviewed actual main_window.py, stylesheet, launcher and latest 0.11.35/34/33/32 notes. No existing historical note rewritten.

## Changes
- main_window.py: persistent read-only active-stage readiness label in the status bar, with the existing truthful readiness detail as tooltip and accessible name; accessible tab names carried forward from #92. Guard unchanged text/accessibility updates. No additional Next button, page order, shortcut or workflow authorization change.
- ui/styles.py: use existing semantic foreground token for the label; retain accepted palette and density system.
- version.py: provisional 0.11.36 only on the 0.11.35 performance stack.
- tools/check_ui2_trainer.py: compare actual native captures of exact parent and candidate, assert visible readiness for the active stage, check changes from empty to synthetic data and back; actual Qt font glyph preflight with recorded platform/family/glyphs.
- .github/workflows/ui2-trainer-visual.yml: Windows uses native Windows Qt platform instead of offscreen; Linux retains offscreen. Failed font probe cannot be counted as valid visual evidence.
- regression.yml: use inherited exact source package checks for unchanged runtime trees with existing strict ancestry and component tree identity conditions; trainer package checked at candidate head.

## Evidence and limits
Previous PR #92 exact 9e0fbaa native CI 46028063043 passed both jobs. Downloaded Linux artifact 15213935053 (94952973521952f042ccec9ecfc007e0c17939d56d06ca855811a038a0233d23) and Windows 15213735418 (e499eb60a695f8b135eb5d0314572cf014d6763b74f35a1d7683a74ce6be6336); all 48 PNG hashes and dimensions independently matched manifests. Linux before/after layouts were broadly consistent, Windows both revisions displayed extensive missing-glyph boxes. Windows visual acceptance rejected despite green CI; new capture correction pending. Parent #93 4d2f66a passed exact workflows 46029004736, 46029004753, 46029004776, 46029004693. New candidate CI, screenshots, full workflow and assistive-technology checks pending; no local Qt execution or visual certification of new source. Main has newer PiSD emulator integration; this stacked trainer-only PR must not be independently merged into main or overwrite it. Reconcile after #93 acceptance. No release/stable promotion.
