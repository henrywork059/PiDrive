# piTrainer 0.11.28 — R51 persistent preprocessing identity

Parent e24eac1 verified Linux 45732670276 and Windows 45732670277 all five jobs. Reviewed current launcher, canonical R51, and notes 0.11.27/26/25/24.

## Change
- services/preprocess/preprocessing_receipts.py: exclusive local JSON receipts with unique ID, UTC completion, recipe and ordered active metadata hashes, actual input session names/directories and captured selection; bounded checksum-verified reads.
- services/preprocess/applied_binding.py and pages/preprocess_page.py: capture after successful Apply, not preview; clear prior association on reset/reapply; guard changed working folder; log receipt failures separately from successful preprocessing.
- pages/train_page.py and services/train/experiment_service.py: attach matching receipt to local run/sidecar; Compare/Inspect shows receipt ID/path or Unknown. Keep recipe/path association and portable manifest schema.
- tests/test_train_runs_r40.py: registered regression for actual source identities, exclusive IDs, collision, edits, root/selection changes, draft edits, persisted run and missing/tampered receipt.
- version.py and shared regression gate notes updated.

## Verification and limits
Guarded exact-parent source edits; CI pending, no local Python/Qt execution claimed. Local metadata hashes are not image hashes or authentication. Receipts are local, not transferred in portable manifests; historical/unavailable links remain Unknown. Receipt writing occurs at Apply completion; failed receipt writes do not block training. Existing UI layout, training algorithm, validation, config, manifest contract and inactive components unchanged. No physical deployment, owner acceptance or stable promotion.
