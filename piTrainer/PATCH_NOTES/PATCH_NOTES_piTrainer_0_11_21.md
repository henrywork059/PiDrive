# piTrainer 0.11.21 — Batch 5 / portable model provenance

- Exported manifests optionally include successful run ID, preprocessing and partition fingerprints, row/group counts without local paths or names. Keep local full experiment sidecars. Validation reads portable provenance if local sidecar absent; mismatched local sidecars remain Unknown.
- Clear previous model-run association before accepting a new successful model; use captured training settings and actual input shape for exports, effective training seed rather than mutable settings; unknown seed when untracked. Fix Keras symbolic-tensor truthiness fallback. Extend mixed-recording export and cross-component tests.

Parent b641f02 verified Linux 45554836806 4/4 and Windows 45554836817 1/1. Reviewed actual entry points and latest four notes per component. Manifest schema v1, legacy behavior, family/input/output/checksum checks, launchers and paths retained. Portable run claims are not authenticated. Exact new CI required; no physical or owner acceptance.

## Data review follow-up (UX61/63/65)
Visible, optional label/AI comparison retains default existing overlay mode and stays synchronized with exact selected frame; accessible slider names and actual Qt selection/sort/filter/toggle tests, real bulk-confirm cancel tests, F1 playback/purge guidance. No edit persistence or row mutation changes. Existing R38 fake renderer harness retains behavior. Exact new CI pending.

## F10 real export gate
Add a CPU-only genuine TensorFlow conversion and interpreter test using deterministic named heads with distinct outputs (-0.25 steering, +0.65 throttle). Run in the clean full dependency smoke environment, not the lightweight test environment. Verify output shape/order and checksum manifest. No training or real Pi deployment; new exact CI must pass.
