# piTrainer 0.11.17 — Batch 4 / R50 label save, validation return and close safety

## Request and root cause
Continue from latest verified 7c7bf08, CI 45421065674 4/4. The existing validation-to-Data navigation was tested but the actual queued label save/return was not. Image Preview edits wait 450ms before saving. MainWindow.closeEvent did not flush the queue before shutdown; _emit_pending_record_edits cleared it before calling the Data save callback and discarded it even after an explicit failure.

## Files changed and behavior
- piTrainer/piTrainer/panels/data/image_preview_panel.py: return a flush success result. Preserve queued records on rejected or exceptional callback; newer same-row queued edits win. Legacy external callbacks that return None remain compatible. Existing debounce timing, controls, navigation and rendering unchanged.
- piTrainer/piTrainer/pages/data_page_filter_edit.py: return True/False to the editor for successful, missing-target, failed or partial metadata commits. Existing messages, atomic-per-file writes, selection and edit-marker updates stay.
- piTrainer/piTrainer/main_window.py: after the active-task close guard, flush outstanding label edits before saving layouts or closing. Ignore close and display error status when save is unconfirmed, retaining dirty edits.
- piTrainer/piTrainer/version.py: advance 0.11.16 to 0.11.17.
- piTrainer/tests/test_validation_to_data_r50.py: expand real native Qt disposable-recording tests with source label save, other-session file untouched, in-memory record and validation mirrored-marker update, frame identity on return, failure/retry and actual Qt close-event veto/acceptance.
- docs/ui_regression_gate.md: record work and remaining Batch 4 acceptance.

## Baseline, anti-rollback and limits
Read exact live main.py route, source callbacks, JSONL edit service, layout/close code and latest plus previous three notes 0.11.16/15/14/13. Preserves recording paths, persistent QSettings layout keys, six-tab workflow, generated-source redirect, session scope, soft-hide/recover and safety guards. A partial labels.jsonl/records.jsonl update is still not a cross-file transaction; retaining the queue permits retry, not rollback of earlier committed files. Test uses temporary folders/QSettings and no motors, Pi hardware, user data or model training. Verification pending exact CI. Coverage remains 35/56 until the remaining R35/R36/R50/UX75 gates pass.
