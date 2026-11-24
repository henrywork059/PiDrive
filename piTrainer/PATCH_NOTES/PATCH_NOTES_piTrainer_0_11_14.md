# piTrainer 0.11.14 — Batch 4 / R50 splitter restore ordering

## Request and observed failure
Native Qt R50 test in CI 45396916022 failed: restored splitter width differed from saved width by 238px. The current restoreState schedules ratio capture after potentially already queued responsive size callbacks; a queued callback can apply constructor defaults before the saved ratio is captured. Qt also constrains restored window geometry to the available display, so absolute sizes alone are not a portable oracle.

## Changes
- pages/dock_page.py: capture restored splitter sizes synchronously after successful Qt restoreState, before deferred responsive callbacks can use stale defaults. Failed restore no longer captures unrelated sizes.
- tests/test_splitter_restore_r50.py: use a window fitting the offscreen display; assert original intended 40/20/40 proportions and compare restored and resized proportions to the original saved ratios, not the restored ratios. Preserve actual DockPage save/restore and temporary INI; test has zero soft minimums.
- Advance existing version series to 0.11.14.

## Verification and limits
Direct parent d134c19; last fully green 299960b (CI 45384279829). Reviewed actual layout class, previous selection/session-control fixes and notes 0.11.13–10. New candidate CI required. Diagnosis is a source-supported race hypothesis, not yet independently confirmed by a passing rerun. No config reset, changes to layout keys, training logic or actual user settings; existing soft-minimum policy retained. Native Windows and real workspace sizing remain separate.
