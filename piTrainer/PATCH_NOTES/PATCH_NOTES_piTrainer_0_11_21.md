# piTrainer 0.11.21 — Batch 5 / portable model provenance

- Exported manifests optionally include successful run ID, preprocessing and partition fingerprints, row/group counts without local paths or names. Keep local full experiment sidecars. Validation reads portable provenance if local sidecar absent; mismatched local sidecars remain Unknown.
- Clear previous model-run association before accepting a new successful model; use captured training settings and actual input shape for exports, effective training seed rather than mutable settings; unknown seed when untracked. Fix Keras symbolic-tensor truthiness fallback. Extend mixed-recording export and cross-component tests.

Parent b641f02 verified Linux 45554836806 4/4 and Windows 45554836817 1/1. Reviewed actual entry points and latest four notes per component. Manifest schema v1, legacy behavior, family/input/output/checksum checks, launchers and paths retained. Portable run claims are not authenticated. Exact new CI required; no physical or owner acceptance.
