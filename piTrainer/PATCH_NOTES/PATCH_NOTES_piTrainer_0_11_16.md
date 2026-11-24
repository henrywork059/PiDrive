# piTrainer 0.11.16 — Batch 4 / R50 unloaded synthetic validation source

## Request and root cause
Continue from exact green candidate 1731528, piTrainer 0.11.15, CI 45418879933 (all four jobs passed). Validation's Edit in Data calls DataPage.focus_record. For a generated/mirrored row whose source session is not yet loaded, _focus_target_record runs before _load_sessions and cannot resolve the original. The existing reload branch only retried source lookup if the *pre-reload* lookup had already succeeded. The generated row stayed selected as the target, but Data review deliberately hides synthetic rows, so focus failed.

## Change
- piTrainer/piTrainer/pages/data_page_sessions.py: after loading the requested session, always re-resolve the original validation record using the existing _focus_target_record helper. This updates the existing redirected status fields when the previously unavailable source becomes available. No new matching rules, cross-session fallback, or source-record mutation.
- piTrainer/piTrainer/version.py: advance existing patch series to 0.11.16.
- piTrainer/tests/test_validation_to_data_r50.py: native Qt end-to-end panel/controller test using a real DataPage, real ValidationFrameReviewPanel, actual MainWindow.open_validation_frame_in_data_editor method, two disposable on-disk label sessions with duplicate frame IDs, and temporary QSettings. Cover unloaded generated source, exact session/image selection, additional session checkbox preservation, validation return identity and already-loaded source without reload.
- .github/workflows/regression.yml: register new native Qt regression in the piTrainer CI component job.
- docs/ui_regression_gate.md: document Batch 4 evidence and open release gates.

## Anti-rollback
Read the current launcher, branch HEAD and the latest four piTrainer patch notes (0.11.15–0.11.12); inspected real DataPage source lookup, source loader and validation callback. No change to model training, filtering rules, original source selection, persistent settings schema, edit/delete behavior, layout keys, other component source, or inactive trees. Existing multi-session preservation and source-frame identity rules remain.

## Verification and limits
Prior 1731528 was green (CI 45418879933). This update's exact CI result must be checked; source review is not an execution claim. Test writes only to a temporary directory and uses isolated QSettings; no real user recordings, model training, Windows native UI, Raspberry Pi hardware or motor actions were tested. Full Batch 4 / owner screenshot acceptance remains open and implementation counts must not advance without acceptance.

## CI test dependency correction
Exact first candidate [CI 45420759869](https://github.com/henrywork059/PiDrive/actions/runs/45420759869) failed in the piTrainer test collection stage before running the new integration test: DataPage imports DataPlotPanel which imports matplotlib; the CI minimal piTrainer test-only dependency set omitted matplotlib. The actual piTrainer requirements already declare matplotlib>=3.8,<4. Add that existing declared range only to the isolated piTrainer CI test dependencies; no app package schema or runtime source change. Re-run exact subsequent candidate and report real test outcomes. Previous registered tests all passed to the point of the import failure.
