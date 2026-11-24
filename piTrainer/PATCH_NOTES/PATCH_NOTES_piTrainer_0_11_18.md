# piTrainer 0.11.18 — Batch 4 / R50 realistic splitter minimum-size allocation

## Request and root cause
Continue from confirmed 0.11.17 at fd5bc3e (CI 45424414919 all four green), after reviewing piTrainer main.py, live DockPage/ResponsiveSplitter, formatting and real Data/Train/Validate splitter presets, current regression workflow and four latest notes 0.11.17–0.11.14. The prior splitter restored proportions successfully for zero soft minimums, but real three-panel workspaces use 260/300/300 (or 260/320/300) px soft minima. On resize with available width exceeding the sum of minima, apply_responsive_sizes assigned each minimum and then distributed *only the leftover pixels* using the saved full-pane ratios. This changes intended proportions even when they fit: for 50:25:25 at 1200px with 260/300/300 minima, the old calculation gives about 430/385/385 instead of 600/300/300.

## Files changed
- piTrainer/piTrainer/pages/dock_page.py — in the feasible-width branch, allocate preferred full-pane ratios first, freezing only panels that would fall below their existing soft minimums, then distribute remaining width proportionally. Integer largest-remainder allocation maintains exact available total and no pane below its soft minimum. Retains existing below-minimum proportional fallback, splitter signals, persisted layout keys and restore timing.
- piTrainer/piTrainer/version.py — bump existing 0.11.x patch line to 0.11.18.
- piTrainer/tests/test_splitter_minimums_r50.py — native offscreen Qt tests using actual Data/Train/Validate presets and real QSplitter panel frames; verify unconstrained ratios, user-defined ratio, constrained widths and exact totals, narrow real geometry and saving/restoring with temporary QSettings.
- .github/workflows/regression.yml — register the new tests in isolated native piTrainer CI.
- docs/ui_regression_gate.md — document R50 evidence and remaining acceptance.

## Anti-rollback and verification
No data labels, models, user QSettings schema, keyboard shortcuts, previous splitters' saveState/restoreState, training, other components, inactive folders or layout topology changed. The pure allocator is tested with exact numeric inputs; Qt narrow-screen behavior and disposable INI restoration are tested separately. Source reviewed; new exact commit CI required to claim passing. Real native Windows desktop, owner visual baseline and physical hardware remain separate. Implementation counts stay 35/56 while Batch 4 gates remain open.
