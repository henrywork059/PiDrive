# piTrainer 0.11.22 — Batch 4 R35 and Batch 5 workflow/provenance

Parent e878c0d verified Linux 45579185459 and Windows 45579185711 successful. Reviewed live launcher, actual source, canonical schedule, workflows and 0.11.21/20/19/18 notes.

## Changes
- main_window.py: require existing file of expected suffix for external model readiness; label retained previous validation results as historical, preserve tab order/icons and task guards.
- panels/train/train_config_panel.py: explicit accessible names for existing form controls; no config behavior changes.
- panels/validation/validation_config_panel.py: exclude directories from Use Latest Export.
- pages/export_page.py and panels/export/model_status_panel.py: show identity-bound training run row counts, epoch count and run ID; unknown provenance stays Unknown rather than showing a newly changed split as training history.
- tests/test_validation_controls_r35.py: native Qt keyboard/names, missing file/directory/real file, historical result and run-bound display regression.
- tests/test_real_tflite_export_f10.py: reuse mixed recording fixture, generate genuine deterministic TFLite with synthetic run claims, upload/load/infer using actual PiSD and PiServer services, test tamper refusal and deletion clears provenance. No motor actuation or training.
- .github/workflows/regression.yml: add OpenCV only to full trainer test environment for actual runtime inference, no production dependency change.
- version.py, shared UI gate: candidate increment and evidence.

## Verification and limits
Parent exact gates passed; new candidate tests await CI. No user data/config changes, no inactive component modifications, no release/merge. Fixture is not trained; provenance claims are not authenticated. Owner visual review, hardware and other uncovered acceptance criteria remain separate; no proposal count increment until evidence.
