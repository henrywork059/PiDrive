# PiSD 0.11.32 — Batch 7 operator workspace candidate

Reviewed live PiSD.py, app, current Manual/Front templates, actual recording status and latest four notes 0.11.31/30/29/28. Parent 581c049 was green; intermediate trainer-only update is retained.

- Component-local bounded recent event ring, API and front-page read-only view: allowlisted endpoint labels, timestamps and response outcomes only; no request content, paths or exceptions. No storage or hardware calls.
- Front page puts Manual Drive/AI first and moves existing STOP/Refresh ahead of workspace cards. Existing links and handlers preserved.
- Manual preview shows last confirmed recording count from existing status field. Group-specific overlay reset edits draft inputs only; existing Apply and full reset remain.
- New unit/API tests registered in CI; version advances. No recording schema, motor, camera, authorization or config schema changes.

Exact new CI pending. API acknowledgement is not proof of physical actuation. Native browser and owner visual approval for new UI remain outstanding; no proposal closure.

Source-review correction: alignment reset keys now match the existing `base_y` and `horizon_y` bindings. No calibration values changed.
