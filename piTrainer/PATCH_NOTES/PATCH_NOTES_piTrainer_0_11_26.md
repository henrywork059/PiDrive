# piTrainer 0.11.26 — Batch 5 plot identity and legacy-model observation (UX64/R51)

Parent b5e9095 verified Linux 45730205838 and Windows 45730205790 all five jobs; PiSD 0.11.36 repair fully green. Reviewed live main.py, current train/validation plot and provenance services, original roadmap requirements and 0.11.25/24/23/22 notes.

## Root cause and changes
- services/train/history_service.py: retain missing values as gaps at actual epoch positions rather than compressing indices.
- panels/train/train_history_panel.py: align partial live metrics by epoch, label dimensionless loss/metric axis (normalized targets, existing MSE/MAE), display captured dataset split fingerprint and recorded session/recipe context; preserve existing plot, artifact copy and unknown-state behavior.
- panels/validation/validation_plot_panel.py: show validation ID and evaluated-row fingerprint, full association/identity in tooltip; dataset selection fallback to recorded dataset name. Existing scatter, histogram, trace and clipboard behavior retained.
- services/validation/validation_provenance.py: when run association is unknown, hash observed legacy model file without claiming manifest verification; before/after context comparison invalidates changed observations. Missing/unreadable file remains unknown. No changes to manifest or model-loading enforcement.
- tests/test_train_runs_r40.py and test_validation_controls_r35.py: missing epochs, observed legacy file replacement, plot axes and identity across all modes, clipboard and stale context. Existing Linux/Windows registration retained.
- version.py and docs/ui_regression_gate.md: candidate/evidence.

## Verification and limits
Source review and guarded edits performed. New exact CI pending; no local Python/Qt execution claimed. Hashes identify metadata/file observations, not image bytes, authenticated run history or immutable inference inputs. A file changed and restored between observations is not detected. No training algorithm, configuration, layout topology, six-tab order, model manifest, motor/STOP or inactive component changes. UX64 is a scoped closure candidate subject to exact CI and review; R51 and Batch 4 remain open. No physical/owner acceptance or release.
