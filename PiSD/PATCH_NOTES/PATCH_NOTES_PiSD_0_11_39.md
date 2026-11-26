# PiSD 0.11.39 — Batch 4 / R35 AI recording-library input parity

Parent e2b85e1 verified Linux 45738242959 (4/4) and Windows 45738242995 (1/1). Reviewed real PiSD.py, canonical R35, current AI template/CSS, shared library/confirmation/keyboard handlers and test registration, and previous notes 0.11.38/37/36/35.

## Cause and changes
- templates/ai_mode.html: named library region and selectors, descriptive notice relationship, initially disabled Download/Delete until verified; existing layout retained.
- static/js/ai_mode.js: native form/control horizontal keyup does not start steering-release loops unless the corresponding drive key was held. Existing release on focus change, pad/body and STOP behavior retained in all three drive modes.
- static/js/recording_download_panel.js: announce selected folder identity and active-recording deletion restriction on verified data only. Retain pending/error notices, timeout, cached selection and exact-target confirmation.
- scripts/test_accessibility_r35.cjs: actual extracted keyup tests across three drive modes and names/initial locks.
- tools/check_browser_ui.py: visible refresh activation, keyboard selection/Tab, mobile taps, exact-target cancel with focus restore and STOP available. Remove hidden-click fallback. Mobile native OS select choice uses select_option after tap; no actual download or deletion exercised. Existing timeout/retry/empty tests retained.
- pisd/__init__.py and shared UI gate notes: version/evidence.

## Verification and limits
Exact parent green; guarded source edits only, exact CI pending. No local browser or hardware execution claimed. No motor authorization, backend STOP, lease, recording-reader, storage/configuration or layout change. R35 remains partial. No merge or stable promotion.
