# PiSD 0.11.16 — R35 keyboard accessibility and input parity

## Request and scope
Implement roadmap R35 in the active PiSD pages: improve focus visibility, native keyboard activation, tablist keyboard navigation and reduced-motion presentation. Do not introduce a new motor control shortcut, bypass the motor-output safety checkbox, change the single global STOP, or revert R31/R32 settings/readiness.

## Baseline and anti-rollback
Branched directly from the previously merged GitHub `main` commit `c615c73032d62daa23ec0fe302d1cfe6049428c3`, containing the previous PiSD R32 draft PR #42 (now merged). Reviewed PiSD patch notes R32, R31, U29 and 0.11.13; inspected real launcher `PiSD/PiSD.py`, both actual `manual_drive.html` / `ai_mode.html`, `global_space_stop.js`, page-specific keyboard guards, existing ARIA tab attributes, and shared CSS. No changes to U28 safety fault latch/rearm, motor backend/authorization, U29 replay or R31 settings.

## Root cause
The capture-phase global Space STOP intentionally listens before native controls. Prior code treated focused checkbox/button input types as candidates for global STOP, so pressing Space on a safety checkbox or STOP button could block its native toggle/click. Manual/AI page keyboard guards also allowed Space through when a checkbox or ordinary button had focus. This is an accessibility conflict and makes keyboard-only setup unreliable. Shared CSS did not provide a uniform high-visibility focus outline or a reduced-motion override.

## Exact files and changes
- `PiSD/pisd/web/static/js/global_space_stop.js` — preserve the global Space-to-STOP on the document body and driving pads, but **do not intercept Space** from focused buttons, links, checkboxes, tab controls or form fields. Native Space/Enter on dedicated STOP controls remains available. The original `/api/ai/stop`, `/api/control/stop`, cooldown and STOP dispatch logic is unchanged.
- `PiSD/pisd/web/static/js/manual_drive.js` — block all page-wide motor/record/snapshot shortcuts when a native interactive control has keyboard focus; preserve keyboard driving when focus is on the page or manual pad.
- `PiSD/pisd/web/static/js/ai_mode.js` — same focus guard for AI Mode. Make AI output tabs conform to roving-tabindex tablist behavior: Left/Right/Home/End focus and activate an output tab through its **existing click handler**, not a new motor endpoint. Existing manual/assist/correction entry, stop rules, save behavior and keyboard commands remain in place.
- `PiSD/pisd/web/static/css/pisd_design_system.css` — shared focus-visible 3px ring with forced-colors support and reduced-motion media query, affecting all PiSD templates that already load this CSS. No geometry, docking, overlay or preview-size changes.
- `PiSD/pisd/__init__.py` — version/cache marker 0.11.15 → **0.11.16**.
- `PiSD/scripts/test_accessibility_r35.cjs` (new) — 11 deterministic native-vs-global-Space cases, including body/pad STOP, checkbox/button/link/tab/textarea/select native behavior, editable content and opt-out zones.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R35.md` — this note.

## Accessibility boundaries
Keyboard controls, form fields and anchored links remain in the natural Tab order; no visual-only color code is relied on to identify STOP. Screen-reader live regions in the R32 readiness strip remain unchanged; no high-rate motor readouts gain live announcements. The AI output tablist is keyboard navigable, with the same backend behavior as pointer activation. STOP still works at the document/pad scope. The application does **not** enable automatic motor output merely because an element is focused or a key was pressed.

## Verification actually performed
- **11/11** pure global Space STOP interaction tests executed in V8 using a CommonJS-compatible adapter, with real final GitHub helper source.
- `global_space_stop.js`, `manual_drive.js` and `ai_mode.js` parsed successfully in V8 after the modifications; presence of control-focus guards checked.
- Current branch comparison vs merged main checked for cross-component changes, deleted files and rollback risk in draft PR description.
- No Python/Flask, browser automation, assistive-technology session, Raspberry Pi camera or physical motor run was performed.

## Known limits
HTML tab focus and visual rendering need on-device browser/keyboard checks before promotion. Testing should confirm Space on safety checkbox toggles it without sending an unintended STOP, that Space on the page/pad still STOPs, that dedicated STOP buttons activate via Space/Enter, and that AI output tabs move with arrow keys without bypassing the existing safety latch.
