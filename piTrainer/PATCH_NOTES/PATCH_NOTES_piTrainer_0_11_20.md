# piTrainer 0.11.20 — Batch 5/6 review context

Parent 581c049: four-job CI 45531850972 and Windows Qt CI 45531851593 passed. Read live main.py, current source and previous four notes 0.11.19/18/17/16.

- Data bulk warning previews representative old/new values from the exact selected records, retains original confirmation and batch update; no change to targets.
- New services/data/review_context.py: pure bounded previews and finite-value prediction comparison. Image Preview displays current label, AI prediction and delta for its own selected record, refreshes during edits and does not treat missing/NaN predictions as zero.
- Validation plot panel: dataset and run context, full run ID tooltip; no changes to metrics.
- MainWindow F1: contextual help, no new shortcuts or changed bindings.
- New deterministic helper tests registered in existing CI; version increment.

No saved layout, label schema, training algorithm, selection routing, export or other component changes. Exact new CI pending. UI visual review and complete native interaction acceptance remain separate. No proposal closure claimed.
