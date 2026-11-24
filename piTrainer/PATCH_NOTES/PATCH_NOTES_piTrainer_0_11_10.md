# piTrainer 0.11.10 — Preserve source-row identity when sorting Records

## Request and root cause
The real offscreen Qt integration test in PR #84, run 45342519579, reproduced a selection identity mismatch after sorting. The table model reordered rows without remapping persistent indexes; the panel attempted to manually restore selection before Qt had completed its own layout-change processing. This can move selection onto another source frame, affecting bulk operations.

## Changes
- piTrainer/panels/data/preview_model.py: map Qt persistent indexes to the same source-row identities after sorting and before layoutChanged; use a source-to-view lookup.
- piTrainer/panels/data/preview_panel.py: remove competing manual selection reconstruction; suppress transient callbacks during sort and refresh after Qt restores selection.
- tests/test_selection_scope.py: retain the original identity regression and strengthen it with exact initial selected identities, repeated sort directions, current and persistent index checks, and an empty selection check.
- piTrainer/version.py: advance 0.11.9 to 0.11.10.

## Baseline and verification
Based on the exact integrated 0.11.9 tree, parent bd9eabf817b808561123dd00384537c4939bc0e0. Reviewed 0.11.9 through 0.11.6 notes and the R37 selection test and implementation. Preserves source mapping, row ordering, bulk selection scope, playback, table layout, settings, and existing visibility/deletion semantics. Existing test failed under native Qt before this change. New commit requires CI rerun; no Windows desktop or physical hardware verification yet. No dataset mutation performed.
