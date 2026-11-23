# piTrainer 0.11.4 — R37 Data selection-scope clarity

## Request
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` **R37**: a lightweight Data Records toolbar showing **Visible / Selected visible / All active / Hidden / Generated** counts. Make bulk-edit affected scope and synthetic-derivative inclusion explicit before overwriting or hiding. Preserve the existing sort-aware read-only `QAbstractTableModel` / `QTableView` with stable source-row identities, filtering, multiselect, and Validation → Edit in Data → Return navigation.

## Baseline and anti-rollback
- Exact base: merged GitHub `main` commit `c615c73032d62daa23ec0fe302d1cfe6049428c3` (piTrainer 0.11.3, U27). Other R33–R36 component drafts #43–#52 remain **unmerged** and do not touch this piTrainer branch.
- Reviewed latest piTrainer notes **0_11_3** (manifest/exports), **0_11_2** (U17 atomic edits and cache safety), **0_11_1** (U11 source-family grouping, U15 unique preprocess export) and baseline **0_11_0**. Inspected actual entry `piTrainer/main.py`, `AGENTS.md`, `pages/data_page.py`, `data_page_sessions.py`, `data_page_filter_edit.py`, `data_page_visibility.py`, `data_page_deploy.py`, `data_page_support.py`, `panels/data/preview_panel.py`, `preview_model.py`, and data loader, synthetic/hidden and edit/delete services.
- Current source has Data Workflow tabs 1 Load, 2 Hide & Recover, 3 Filter, 4 Review, 5 Deploy. No tabs, panel docking or widget hierarchy are reorganized by this patch; no item-based table is introduced.
- Preserve V11 multi-session selection, stable source-row mapping, default chronological sort, first-column horizontal anchor, Up/Down navigation and Validation → Data → Return focus; generated-source redirect; R31 and U17 file-safe atomic JSONL edits, source image preservation, and non-overwriting model manifest exports.

## Root cause / prior gap
The Record Preview table already supported multi-select, filtering and header sorts, but its summary mixed the current row, visible total and selected count. The separate bulk-edit panel displayed only `Selected: N`, leaving it unclear whether actions targeted **all loaded active frames**, **all currently filtered rows**, or only the **selected visible** rows. Synthetic derivatives are excluded from Data review by default but remain legitimate loaded training examples, so a simplistic frame total would obscure them. Hidden rows are excluded from active dataframes; counting them from the preview or training set would produce a misleading 0. Additionally, a record dictionary converted from a sparse pandas dataframe can contain `NaN` synthetic-flag columns; a scalar truthiness check can erroneously report generated rows. R37 uses the established NaN-safe vectorized synthetic mask.

## Exact semantics
- **Visible:** number of filtered source rows *currently rendered in Records*, after the existing Data-page preview filter and synthetic exclusion.
- **Selected visible:** number of real QTableView-selected **source rows** (the existing `selected_source_rows()` mapping), not a tab focus/current cell or selection from another table.
- **All active:** count of **non-hidden loaded dataset rows**, before the Data-page preview filter and train-only-manual restrictions; includes generated derivatives. It is **not** the number of frames that will be edited.
- **Hidden:** unique hidden frame identities in the loaded sessions' `labels.jsonl` / `records.jsonl`, counted with the existing hide/recover matching identities and deduplicated across metadata files. Scanned **once on session load or reload** and incremented after a successful Hide Selected. Unreadable metadata displays **Unavailable**, never an invented zero.
- **Generated:** synthetic/augmented rows in the active loaded dataframe (`s_` IDs, flags or non-original variants). They are excluded from Data review by default. Any synthetic selected rows, if a future review configuration exposes them, are disclosed accurately by the shared `synthetic_row_mask()` vectorized against records, avoiding sparse `NaN` misclassification.
- A filter, sort or Shift/Ctrl multiselection updates **Selected visible** without reading all JSONL files or replacing the model. **Select Visible** targets current preview rows only, not all loaded rows.

## Files changed
1. `piTrainer/piTrainer/services/data/selection_scope.py` **new** — read-only immutable count summary, clear count definitions, precise affected-scope wording, NaN-safe generated-row classification.
2. `piTrainer/piTrainer/services/data/delete_service.py` — new public `count_hidden_frames()` reusing existing `_hidden_refs` metadata matching/dedup, with no mutation and no new path scheme.
3. `piTrainer/piTrainer/panels/data/preview_panel.py` — two-line lightweight count/meaning strip **above** existing summary and `CyclingPreviewTable`; refreshed by existing selection/sort signals and `set_scope_totals`. Keeps model source-row mapping and keyboard navigation intact; no QTableWidget added.
4. `piTrainer/piTrainer/panels/data/bulk_edit_panel.py` — explicitly label count `Selected visible` and clarify Select Visible tooltip; preserves overwrite checkbox, centred sliders and existing apply actions.
5. `piTrainer/piTrainer/pages/data_page.py` — initialise loaded-hidden metadata state.
6. `piTrainer/piTrainer/pages/data_page_sessions.py` — capture actual **loaded** session names and scan the cached hidden count after loading, without modifying the current session selection.
7. `piTrainer/piTrainer/pages/data_page_support.py` — refresh count summaries from the actual loaded dataset, filtered preview and selected QTable source rows; unknown hidden metadata remains unknown.
8. `piTrainer/piTrainer/pages/data_page_filter_edit.py` — refresh counts on filter and show exact selected-visible/generated impact plus all-loaded distinction before steering/speed batch edit. Existing U17 atomic writer and first-identity reselect remain unchanged.
9. `piTrainer/piTrainer/pages/data_page_deploy.py` — before applying AI predictions, distinguish **eligible selected visible** frames, any selected frames without usable predictions, generated inclusion and all-active loaded count. Preserve original same-identity update path.
10. `piTrainer/piTrainer/pages/data_page_visibility.py` — multi-frame Hide Selected gets a default-No warning with count and synthetic inclusion **in addition to** the prior Confirm Hide checkbox; single-frame hide remains the previous workflow. Only an unambiguous successful hide increments the cached count. If any metadata write reports a partial failure, the count becomes **Unavailable** until the sessions are reloaded. Recover/purge reloads continue using the existing service and selection-preservation workflow.
11. `piTrainer/piTrainer/version.py` — patch version **0.11.3 → 0.11.4**, existing naming scheme `piTrainer_0_11_4`.
12. `piTrainer/tests/test_selection_scope.py` **new** — 19 unit cases: 14 pure-data count and NaN/generated/scope tests, 4 JSONL hidden counting cases, and one optional PySide6 offscreen source-identity sorted multiselect + explicit frame reselect test.
13. `piTrainer/README.md` — document what the five counts mean, bulk scope and loaded-session metadata refresh behavior.
14. `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_4.md` — this note.

## Verification actually performed
- Exact `selection_scope.py` Git blob hash **57615c167b7dcf1e22ece3f99609d0680cc7be89** reproduced in a local verification copy.
- **16/16** local direct pure-data/selection checks passed using that exact hash-matched new helper and the **compatible older uploaded visibility-service fixture**. This exposed and corrected a real sparse-pandas `NaN` selected-synthetic miscount before committing the final helper. Checks included filtered vs all-loaded totals, selected-only targets, legacy synthetic flags, unknown vs zero hidden, reversal of selected order, non-mutating input, generated exclusion and empty datasets.
- The **19-case committed Python test suite was NOT executed end-to-end** against the full latest GitHub tree here. Its four disk-metadata cases and the offscreen Qt test have not run; PySide6 is not installed in the local verification environment. Do **not** interpret 16 helper checks as 19/19 passed.
- GitHub compare against current main, component-only scope and no file deletions to be verified before opening draft PR.

## Known limits / next steps
- Reading hidden metadata on session load adds one extra metadata scan. It is deliberately **not** done for each selection/sort, but may add load latency with very large datasets; measure this during R38.
- If an external process changes JSONL after load, reload sessions to refresh the cached hidden count. A failed/unreadable scan displays Unavailable; counts are informational, not an authorization mechanism.
- Exact affected **selected view-row** count is disclosed before the action. Some metadata identities may fail or map to multiple JSONL entries: actual successful rows/matches continue to be reported by existing U17 result handling. The UI does not promise success before an atomic write completes.
- Full `python -m unittest discover -s tests -v`, Python compilation from the latest branch, real Windows PySide6 GUI, Validation → Edit in Data → Return and source-sorted Shift/Ctrl multi-selection must be run before promoting from draft. No real recording or personal session data has been edited.
