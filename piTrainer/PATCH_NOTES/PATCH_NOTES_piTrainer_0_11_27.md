# piTrainer 0.11.27 — R51 portable model provenance inspection

## Request and cause
Parent f0e33f6 verified Linux 45732321702 and Windows 45732321842, all five jobs. Reviewed actual main.py, current Compare/experiment services, manifest contract and 0.11.26/25/24/23 notes. Inspect Model previously required a desktop experiment sidecar even when the portable manifest contained a verified file checksum and experiment claim; an existing local run with the same ID could obscure the selected model's metadata.

## Changes
- services/train/experiment_service.py: read-only inspection for verified local records, portable manifest claims or observed legacy file hash. Missing session names, paths and run details stay unknown; present invalid local sidecar or invalid manifest fails closed. Source group count exposed without inventing group identities.
- panels/train/train_comparison_panel.py: show selected model's own metadata and exact checksum-matched local validation receipts, distinct from run-ID matches. Portable claims never insert or replace local history; verified local sidecars retain selector support. Refresh/select restores existing comparison.
- tests/test_train_runs_r40.py and test_validation_controls_r35.py: portable/legacy inspection, missing links, no fabricated local records, invalid sidecar/tamper, exact receipt selection and local selector preservation. Existing CI registration retained.
- version.py and docs/ui_regression_gate.md: candidate/evidence.

## Verification and limits
Source review and guarded edits only; new exact CI pending, no local Python/Qt execution claimed. Manifest checksum verifies model bytes, not authenticity of provenance; legacy checksum is observation only. Matching receipt hash establishes file identity, not physical deployment or verified historical training. Local receipts are bounded to loaded history. Model inspection hashes files synchronously as existing local inspection did; large files can delay the UI. No persistent config, manifest schema, model load enforcement, training, validation math, six-tab order, layout topology or inactive component changes. No release/merge or owner/hardware acceptance. R51 closure requires verified review of complete chain.
