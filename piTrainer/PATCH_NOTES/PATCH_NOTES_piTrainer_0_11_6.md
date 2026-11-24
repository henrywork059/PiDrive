# piTrainer 0.11.6 — R39 Unified Background-Task Progress

## Request and acceptance
Implement roadmap **R39** from `docs/roadmaps/PiDrive_Refinement_Roadmap.md`: make long-running preprocessing, training, validation and model export nonblocking; show each operation's current step and measurable progress; allow stop only when backend supports a safe boundary; distinguish succeeded / failed / cancelled; show exact verified output paths; never treat incomplete artifacts as successful.

## Exact baseline, patch history and anti-rollback
- Branch: `update/pitrainer-0_11_6-r39-background-progress`, created from the **R38 draft PR #54** head `0e66d22f7dfc666731bd2dece240488090720a8b`; draft PR must be stacked on that R38 branch and **not** merged automatically.
- Inspected the live roadmap, actual `piTrainer/main.py`, `piTrainer/piTrainer/main_window.py`, Train/Preprocess/Validate/Export/TFLite Check page sources, existing QThread training worker, control panels, preprocessing and model export services, and version `0.11.5`.
- Reviewed component notes `0_11_5` (R38 bounded QPixmap cache/coalesced preview), `0_11_4` (R37 scope identities), `0_11_3` (model manifests), `0_11_2` (atomic label metadata); keep all those accepted behaviors unchanged.
- No Data page records, dataset loader, augmentation recipe logic, validation backend, image preview, QPixmap cache, docking layout, runtime configuration, user recordings or legacy components were replaced. The patch is confined to `piTrainer/`.

## Root causes
1. Training used a QThread and percent-per-epoch signal but unconditionally emitted `training_finished` after `model.fit`, even when `request_stop` had stopped an epoch. The page would accept partial weights and report success.
2. Preprocess apply/preview/save, model export, trained-model save, Keras validation and TFLite validation ran their expensive work directly from GUI callbacks and could block Qt painting/input.
3. Export and saved-dataset UI reported successful results from return values without checking all expected output files; converter/manifest failures could leave partial disk artifacts, and the status displays lacked one shared lifecycle vocabulary.

## Changes by file
1. `piTrainer/piTrainer/services/background_task.py` (new): one-shot `QThread` function worker and page-owned runner, GUI-thread completion/failure callbacks, indeterminate or measured step signal, disabled re-entrant controls, failure propagation even for post-work verification errors, and worker lifetime retained until `QThread.finished`. No unsafe stop/terminate method.
2. `piTrainer/piTrainer/panels/common/task_progress_panel.py` (new): common step, progress and selectable output-label widget, with explicit **Succeeded / Failed / Cancelled** rendering, indeterminate bars when no percent is meaningful, and 100% only after verified completion.
3. `piTrainer/piTrainer/services/task_outputs.py` (new): pure shared filesystem verification of nonempty model files **and matching `<model>.manifest.json`**, or all three preprocessing CSV/JSONL/recipe files. Fail closed rather than confirming partial outputs.
4. `piTrainer/piTrainer/services/train/worker.py`: training setup/review/model/epoch phase messages; explicit stop acknowledgement at a safe epoch boundary; dedicated `training_cancelled` signal instead of emitting training success for a stopped run; normal early stopping remains completion.
5. `piTrainer/piTrainer/pages/train_page.py`: common task status for training, cancellation/failure state, stop-button lock after a stop request, asynchronous non-overwriting Save Model + manifest writing, and exact confirmed saved paths. Cancelled weights are not adopted as the new in-memory model.
6. `piTrainer/piTrainer/pages/preprocess_page.py`: background preview, recipe apply and processed-data save from captured data/settings; final state/UI changes on the GUI thread; dataset identity guard discards stale background apply/preview results; saved dataset paths confirmed before success. Preserve the existing flip/synthetic/scope recipes and applied-row state updates.
7. `piTrainer/piTrainer/services/export/export_service.py`: optional phase progress callback around Keras saving, TFLite conversion and manifest writing; 100% is reported only after manifests are published. Existing API callers without callback continue working.
8. `piTrainer/piTrainer/pages/export_page.py`: QThread export and checked artifact/manifest paths, old status/log/TFLite-check linking retained only after verified completion.
9. `piTrainer/piTrainer/pages/validation_page.py` and `pages/export_validation_page.py`: background inference with a source/config snapshot, existing plots/result/frame review retained and updated on GUI thread. These checks create no model files.
10. `piTrainer/piTrainer/main_window.py`: serialize background actions across the five workflow pages to avoid competing TensorFlow/model/dataset operations; refuse app close while a worker is active (request safe training stop, but do not terminate non-cancellable workers).
11. `piTrainer/piTrainer/version.py`: patch `0.11.5` → `0.11.6` / `piTrainer_0_11_6`.
12. `piTrainer/tests/test_background_tasks_r39.py` (new): pure output presence/size tests, source AST parse smoke test and optional PySide6 worker signal/status tests.
13. `piTrainer/README.md`: operator workflow, limits, checks and output/cancellation semantics.
14. `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_6.md`: this note.

## Verification actually performed
- Verified baseline R38 PR #54 remained an open unmerged draft with parent R37 #53 and expected head SHA before branching. Fetched the current repository paths directly from GitHub rather than relying on an older zip.
- Created a local exact-text copy of the new `services/task_outputs.py`: its Git blob SHA **`ce2fe39c0a903acf6b544d70c760afa74cc454d5`** matched the live R39 GitHub blob exactly.
- Ran **12/12** local Python 3 standard-library filesystem checks against that exact hash-matched module: confirmed models and both manifests, empty/missing models/sidecars, duplicate outputs, absolute paths, complete dataset, missing dataset directory/JSONL, and zero-length recipe.
- The **16-test committed** `test_background_tasks_r39.py` file is included but **has not been run end-to-end against the GitHub branch**. It contains 13 standard-library/output/AST cases plus 3 optional offscreen PySide6 tests. The optional tests are unrun because PySide6 is absent from this Linux container.
- Reviewed source modifications and GitHub branch comparison against R38: all changes are within `piTrainer/`, zero file removals, no modifications to R37/R38 selection/preview modules. The full Windows GUI integration suite, real TensorFlow training/conversion, and PySide6 QThread run have **not** been executed in this environment.

## Limits / release gate
- Cancellation is **only** exposed for Keras training, at an epoch boundary. It can take time to finish the current epoch and associated review work. No unsafe Stop for conversion, preprocessing, file writes, or inference. Closing the app while any worker is active is refused; user must let it finish or allow training to stop.
- TensorFlow converter operations may leave a partial model/directory after an exception; failure is surfaced and those paths are **not** confirmed. Cleanup/atomic publication of model exports is a separate follow-up, not silently asserted by this patch. The independent `<model>.manifest.json` contract from U27 is unchanged.
- Background progress is **indeterminate** for operations with no measured work units. Training epochs provide actual percent, and export reports genuine phase boundaries/manifest completion; no time-based percentages are fabricated.
- Before promoting from draft, on the target Windows/PySide6/TensorFlow setup run `cd piTrainer && python -m unittest discover -s tests -v`, verify real training stop/early stopping, model save/export and manifest inspection, 10,000-row preprocess preview/apply/save, Keras/TFLite frame results and navigation, reentrant task/close protections, and R37 scope/R38 rapid preview + 450 ms metadata edits.
