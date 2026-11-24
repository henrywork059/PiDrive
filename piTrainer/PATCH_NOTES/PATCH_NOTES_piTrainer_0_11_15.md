# piTrainer 0.11.15 — Batch 4 / R50 validation edit marker lifecycle

## Request and root cause
Continue Batch 4 from green ffa507d (CI 45416643320). ValidationFrameReviewPanel stored edited group keys across successive result objects. A fresh validation could therefore highlight frames as "Edited in Data after this validation run" based only on edits made before that run, incorrectly implying the new predictions were stale.

## Files changed
- piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py — clear edited group keys when set_result receives a different result object, including None; retain them when refresh_from_state re-sends the same mapping. No change to selection logic or mirrored-frame matching.
- piTrainer/piTrainer/version.py — advance candidate from 0.11.14 to 0.11.15.
- piTrainer/tests/test_validation_marker_lifecycle_r50.py — native offscreen Qt regressions for source/mirrored edits, collision isolation across sessions with identical frame IDs, same-result refresh, new run, clear/reload and stable Edit-in-Data selection across sorting.
- .github/workflows/regression.yml — include new test in existing piTrainer isolated regression matrix.
- docs/ui_regression_gate.md — record R50 coverage and remaining acceptance.

## Baseline and anti-rollback
Inspected actual main.py launcher, main_window.py validation-to-data route, ValidationPage refresh, ValidationFrameReviewPanel and validation_preview_rows, current version, latest notes 0.11.14/13/12/11, and the verified ffa507d development HEAD. All existing six-tab flow, Data/Validation selection, saved layout/splitters, soft-hide/recover, source/mirror editing and native shortcuts remain. The identity check relies on the existing design where a fresh validation builds a new result dict and refresh passes the existing dict.

## Verification and limits
Source and test design inspected. Prior ffa507d CI 45416643320 fully green. This version's exact four-job CI must pass before describing it as verified. Tests use in-memory synthetic validation rows only; they do not train, overwrite records, or exercise actual image decoding. Native Windows and Raspberry Pi hardware, full real-workspace UI acceptance and approved golden screenshot comparisons remain open. No Batch 4 completion-count increment.
