# PiServer 0.4.39 — Batch 4 / UX75 saved-folder refresh ordering

## Request and root cause
Continue from 7ec1be7 (CI 45517818839, all four jobs passed). The saved-folder GET captured selection before waiting and applied every result regardless of newer reads or confirmed deletion. A slow response could reset a user's choice, resurrect an already-deleted folder in the UI or overwrite newer feedback.

## Files and behavior
- PiServer/piserver/web/static/app.js: in-memory request generation guards success and error paths, selection read on response, existing fallback retained, confirmed deletion invalidates older reads; explicit Refresh reports only a current result/error. Superseded optional recording reads do not throw a false failure.
- PiServer/piserver/app.py: version marker only.
- PiServer/tests/test_session_refresh_ux75.cjs: nine deterministic tests of actual functions with deferred GET/POST responses; registered in .github/workflows/regression.yml.
- docs/ui_regression_gate.md: evidence and limitations.

## Anti-rollback
Read actual launcher, current JS/API, current regression workflow, canonical main roadmap and four previous notes 0.4.38/37/36/35. Preserve existing recording acknowledgement, 3500ms GET timeout, model/status revisions, exact-target delete confirmation, fallback, settings, storage and motor/STOP behavior. No data migration or inactive component changes.

## Verification and limits
Parent full gate green; exact candidate CI pending. Deterministic tests cover local request ordering, not distributed ordering, physical hardware, native Windows or owner visual acceptance. Existing native Chromium gate retained; no new browser scenario claimed. Progress stays 35/56; Batch 4 open.
