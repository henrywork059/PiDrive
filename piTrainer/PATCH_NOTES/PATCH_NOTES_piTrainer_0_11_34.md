# piTrainer 0.11.34 — Performance Update 2.2 bounded JSONL ingestion (provisional)

Package baseline: 7fa1807bccb4140ad8ba8ed904e5d912f379cf44
Original performance comparison baseline: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7

## Request, cause, and forward baseline
Make large recorded-session JSONL ingestion bounded while retaining exact record visibility, source priority and dataset labels. Previous loader created a complete per-session label list, then another usable list and copied each into a global row list; large sessions had transient object-reference growth. Continues 0.11.33 and prior three notes. Next 0.11.34 absent from current/main tree before allocation. No stable promotion.

## Changes
- piTrainer/piTrainer/services/data/record_loader_service.py: generator-driven labels and records with compatibility list wrappers, single-row primary-label probe and unchanged labels-over-records fallback/hidden identities, bounded 1..4096 row batches (default 512), existing full final DataFrame schema and coercion unchanged. No asynchronous loads or augmentation caching.
- piTrainer/piTrainer/version.py: provisional candidate marker.
- piTrainer/tests/test_record_streaming_p2.py: deterministic fixture comparing original list helper output, order, metadata and bounded iterator across batch sizes.
- .github/workflows/regression.yml: mandatory Linux piTrainer regression.
- Roadmap: partial P2.4 evidence.

## Verification and outstanding qualification
Candidate committed for full Linux/Windows/strict review CI; before combined results it is not accepted as a resource gain. Final DataFrame still materializes all rows, so this reduces transient per-session buffering, not total dataset RSS to a fixed bound. No change to saved configs, split/seed, provenance, export, row identity, random augmentation, UI or model family. Real large-dataset RSS/epoch and native Qt acceptance pending.


## Revision 2.3 — real interpreter qualification
Parent 1b02da5 passed all ten jobs. Strict trainer artifact 15208531867 SHA256 cfb72ac52fb7be898f5fc374896008220dfc0bb542e4acbfeaf67f158acfc682: review p95 161.794→19.149 ms, RSS 343.789→304.719 MiB, CPU 9.175→5.512s, semantic parity. Strict cache 15208950468 SHA256 aeb0fb3ae29dafc5869dbf0c7ff7e7e01218e6e9eda4635213ec493f2f0d8b19 parity. Existing real exported-model regression now runs five paired offline interpreter thread comparisons with the actual export and eight seeded prepared tensors, preserves JSON artifact and asserts exact output digests. Synthetic constant-head fixture is not a representative trained model; no local TensorFlow runtime or actual Pi measurements claimed. Existing production defaults unchanged; provisional version retained.
