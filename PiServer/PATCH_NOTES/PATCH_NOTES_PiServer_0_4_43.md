# PiServer 0.4.43 — Batch 4 / R35 diagnostic keyboard input parity

Parent 3024919 verified Linux 45736191148 and Windows 45736191153 all five jobs. Reviewed live server.py, current app/template/style, existing regression workflows, original R35 acceptance and 0.4.42/41/40/39 notes.

## Cause and changes
- piserver/web/static/app.js: manual-drive global keydown previously intercepted native disclosure Space and event-log navigation keys. Ignore diagnostic/control targets while preserving body/pad input and unconditional existing keyup release within manual workspace.
- templates/index.html: name the read-only focusable event log and mark it as excluded from drive keydown.
- static/styles.css: shared normal/forced-colors focus for summary and suppress button hover translation in reduced-motion mode only. Joystick geometry transforms untouched.
- tests/test_accessibility_r35.cjs: actual extracted key handlers check diagnostic suppression and preserved drive/release behavior.
- tools/check_browser_ui.py: actual manual-page diagnostic keyboard disclosure, tab/clipboard, event log keydown state and mobile tap at four widths; all mutations remain intercepted.
- piserver/app.py and shared regression gate notes: version/evidence.

## Verification and limits
Guarded exact-parent edits, parent CI verified; new exact CI pending. No local execution claimed. No config, API, authorization, motor algorithm, STOP, layout storage, recording or model contract changes. Hardware safety acceptance separate; R35 remains partial pending broader active-control/touch audit. No merge or stable promotion.
