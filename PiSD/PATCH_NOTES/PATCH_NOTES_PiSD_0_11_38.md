# PiSD 0.11.38 — Batch 4 / R35 action-log disclosure and keyboard isolation

Parent c36ad1a verified Linux 45737070868 (4/4) and Windows 45737070765 (1/1). Reviewed real PiSD.py, current Manual Drive template/keyboard handlers/CSS, R35 acceptance, registered test suites, and notes 0.11.37/36/35/34.

## Cause and changes
- templates/manual_drive.html: explicit action-log disclosure relationship/expanded state; name and make the existing scrollable log keyboard-focusable; mark read-only text as exempt from global Space STOP, matching existing front diagnostics.
- static/js/manual_drive.js: synchronize expanded state with existing hidden attribute; exclude marked log from drive/capture keydown; allow native horizontal keyup when no matching drive key is held, but preserve release of held steering after focus changes.
- scripts/test_accessibility_r35.cjs: actual extracted guard, disclosure/focus and global Space exclusion checks; preserve all existing body/pad STOP tests.
- tools/check_browser_ui.py: actual four-width disclosure Space, Tab traversal into named log, keyboard focus and no mutation on arrow/Space/r/s; narrow touch toggle; existing pad Space STOP regression retained.
- pisd/__init__.py and shared gate notes: version/evidence.

## Verification and limits
Parent exact CI green, new exact CI pending; no local browser execution claimed. No changes to motor authorization, backend STOP, lease, recording reader, data/configuration or layout. New log exemption is limited to the marked read-only element; body/pad and explicit STOP buttons retained. No physical safety or owner acceptance. Broader R35 control audit remains open.
