# piTrainer 0.11.23 — Batch 5 workflow milestones and plot context

Parent 04dbfd9 verified all five jobs, Linux 45580547411 and Windows 45580547521. F10 recording-to-model contract met at automated scope. Reviewed real main.py, previous notes 0.11.22/21/20/19, current workflow and original acceptance criteria.

## Changes
- main_window.py: distinguish Done, Inputs available and Needs input for existing six tabs. Data, preprocessing and trained model markers are local milestones; export is confirmed only for the same model object and still-existing nonempty outputs. Validation results remain historical; never certify changed inputs.
- pages/export_page.py: retain successful export model identity and confirmed file paths in memory only; no user config or disk schema change.
- pages/train_page.py and panels/train/train_history_panel.py: keep active plot history/context during a running training operation, identify captured run, source-group count, split counts and recorded artifact paths; no fabricated linkage. Saved/linked artifacts refresh plot context. Existing history plots retained.
- panels/validation/validation_plot_panel.py and services/validation/validation_plot.py: captured model source/path and checksum, selectable plain-text context, clear stale tooltips, label normalized control axes and frame counts. Existing plot calculations retained.
- tests/test_validation_controls_r35.py: exercise done/readiness, model-bound export path guard, plot context and clearing. Already registered on both Linux and native Windows.
- version.py and docs/ui_regression_gate.md: candidate version and evidence.

## Anti-rollback / verification
No changes to model algorithms, validation math, artifact naming, training settings, tabs/order, saved UI layout, motor/camera safety or inactive components. Parent gate green; exact new candidate CI required. No actual training, owner visual approval or hardware deployment. Export marker indicates confirmed local output files, not checksum revalidation or deployment. Validation results remain historical, and no Batch 4/5 completion is claimed solely from this patch.
