# PiSD 0.11.30 — Batch 4 / R35 keyboard dialog containment

## Request and cause
Manual overlay and AI rate dialogs were modal in markup but lacked Tab wrapping. AI also refocused an input after asynchronous settings readback, potentially stealing focus, and did not explicitly suppress driving shortcuts while the rate dialog was open.

## Changes
- Add component-owned dialog_focus.js, loaded by existing Manual and AI templates, to wrap Tab/Shift+Tab only between visible enabled controls.
- Set initial focus synchronously on open, keep existing Escape and close focus restoration. AI modal suppresses local drive shortcuts while open; global Space STOP and dedicated STOP routes retain existing handlers. No change to motor commands, lease, persisted settings, geometry or visual defaults.
- Shared Chromium fixture now verifies modal keyboard focus cycle, Escape/return focus, empty recording/model libraries and intercepted STOP dispatch at the four widths. Native Qt splitter persistence check added separately.
- Version 0.11.29 -> 0.11.30.

## Verification and anti-rollback
Direct parent 299960b (CI 45384279829 4/4, all 16 browser cases); reviewed current Manual/AI JS/templates and latest four notes 0.11.29–26. Previous saved speed/limit/overlay startup regression stays enforced. No persistent files or inactive component changes. New exact-candidate CI pending; screenshot approval and physical/native Windows acceptance separate. Dialog keyboard loop is not a hardware safety guarantee.
