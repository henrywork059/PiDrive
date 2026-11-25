# piTrainer 0.11.24 — Batch 5 persistent validation provenance (R51/UX64)

Parent e9234ab verified Linux 45601026674 and Windows 45601026527, all five jobs. Reviewed live main.py, current validation/result/experiment services, 0.11.23/22/21/20 notes and canonical requirements.

## Root cause and change
Validation results had model/run context but were only held in memory; the Compare panel required two distinct runs before showing even a single run's details.
- services/validation/validation_receipts.py: local version-1 summary in captured working folder/validation_runs, fresh exclusive-create ID, actual evaluated row/label hash, captured association, model checksum when known, dataset source, metrics. No image bytes; unknown historical fields remain null. Bounded reader skips malformed summaries.
- pages/validation_page.py and export_validation_page.py: write receipt after inference completes in existing background worker, log saved path or separate save failure without falsely failing inference.
- services/validation/validation_result.py and panels/validation/validation_plot_panel.py: display receipt ID, path and fingerprint context; existing plots retained.
- panels/train/train_comparison_panel.py and pages/train_page.py: show single selected run even without comparison partner, latest five local validation summary paths linked by training run ID; accessible run selectors; preserve existing two-run comparison.
- tests/test_train_runs_r40.py and test_validation_controls_r35.py: identity, no overwrite, missing fields, corrupted receipt, single-run read-only view and plot receipt path regression. Existing Linux and Windows test registration retained.
- version.py and docs/ui_regression_gate.md: candidate/evidence.

## Limits and anti-rollback
No new production dependencies, existing training/model/export behavior, file naming, settings, six tabs and layout topology preserved. Receipts are local observational summaries, not authenticated records or proof of actual deployment. Historical models without provenance remain unknown. Exact new CI pending; actual hardware and owner visual approval not performed. No proposal closure until verified. New local validation summaries are generated only after successful validation/check; they contain metadata, not images or per-frame predictions. Interrupted writes can leave a corrupt receipt, which the bounded reader skips.
