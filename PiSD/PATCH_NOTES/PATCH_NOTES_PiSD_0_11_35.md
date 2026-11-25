# PiSD 0.11.35 — Batch 4 recording-library recovery (UX75/R35/R50)

## Request and root cause
Continue from fully verified 95537b4 (Linux 45621207251 4/4, Windows 45621207058 1/1). Manual and AI folder listing lacked a deadline and response-order protection; a failed HTTP response could be rendered as empty or leave stale actions available.

## Changes
- pisd/web/static/js/recording_reader.js: shared read-only 3500ms deadline through JSON body, abort superseded reads, generation guard, strict success/collection shape check.
- manual_drive.js and recording_download_panel.js: retain cached selection on failure, explicitly unverified cached details, disable Download/Delete until verified, preserve error on kind/selection changes, recheck target after exact-target confirmation, locally remove confirmed deletion before refreshing. Existing server mutation semantics and STOP remain independent.
- manual_drive.html and ai_mode.html: load shared reader; announce existing notice with polite status region.
- tools/check_browser_ui.py: four-width Manual/AI synthetic populated/stalled/rejected/recovered/empty folder tests, mobile tap when visible; hidden controls exercise actual handler rather than claim touch-only workflow. All mutations intercepted.
- pisd/__init__.py and docs/ui_regression_gate.md: candidate version and evidence.

## Anti-rollback and verification
Reviewed actual PiSD.py, live recording endpoints, current scripts/templates, original R35/R36/R50/UX75 requirements and four prior notes 0.11.34/33/32/31. No persistent settings, motor/camera algorithms, recording schema, authorization, inactive components or layout topology changed. JS syntax parsed before commit. Parent exact CI green, new exact CI pending. No new proposal closure claimed, no physical hardware/owner visual acceptance. Cached metadata is not proof the folder still exists; backend remains authoritative.
