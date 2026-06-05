# PATCH NOTES — piTrainer_0_9_8 Deploy File Packaging Repair

## Request summary

Fix the startup crash reported after applying the latest v9 patch:

```text
ModuleNotFoundError: No module named 'piTrainer.panels.data.model_deploy_panel'
```

## Cause / root cause

The Data page imports the new deploy UI module introduced by the model-deploy feature. If a user applied the later tab-order patch without also having the deploy files from `0.9.6` present, `data_page.py` referenced `piTrainer/panels/data/model_deploy_panel.py` but that file did not exist in the local project folder.

This was a patch-delivery dependency problem, not a typo in the launch command and not a problem with `main.py`.

## Files changed

This repair patch deliberately re-includes the deploy feature files that the current Data page needs at startup:

- `piTrainer/piTrainer/pages/data_page.py`
  - Keeps the corrected Data Workflow tab order: `4 Review`, `5 Deploy`.
- `piTrainer/piTrainer/panels/data/model_deploy_panel.py`
  - Re-included so the Data page import resolves.
- `piTrainer/piTrainer/services/data/model_deploy_service.py`
  - Re-included so the deploy panel backend resolves.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Re-included to preserve the deployed-output overlay and the `0.9.5` Up/Down focus fix.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Re-included to preserve deployed-output columns and difference sorting.
- `piTrainer/piTrainer/services/data/preview_service.py`
  - Re-included to preserve deployed-output table column ordering.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.8 / piTrainer_0_9_8`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_8.md`
  - This patch note.

## Exact behavior changed

- The app should no longer crash on startup from a missing `model_deploy_panel.py` module.
- The Data Workflow order remains:
  1. `1 Load`
  2. `2 Hide & Recover`
  3. `3 Filter`
  4. `4 Review`
  5. `5 Deploy`
- The model deploy feature remains available in `5 Deploy`.
- The deploy overlay, deployed-output columns, and diff sorting support are preserved.

## Behavior intentionally not changed

- No new deploy workflow behavior was added in this patch.
- No preprocessing, training, validation, export, or TFLite conversion logic was intentionally changed.
- The `0.9.1` session working-folder behavior is preserved.
- The `0.9.1` playback FPS maximum of `250` is preserved.
- The `0.9.2` Hide & Recover workflow and hidden permanent-delete shortcut are preserved.
- The `0.9.3` and `0.9.4` wording cleanups are preserved.
- The `0.9.5` Image Preview Up/Down navigation focus fix is preserved.
- The `0.9.7` tab-order correction is preserved.

## Rollback-risk check

Checked against the latest current code state plus the latest v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_7.md`
- `PATCH_NOTES_piTrainer_0_9_6.md`
- `PATCH_NOTES_piTrainer_0_9_5.md`
- `PATCH_NOTES_piTrainer_0_9_4.md`

This patch is a forward repair. It does not remove the deploy feature or revert the corrected tab order.

## Verification actually performed

- Reproduced the risky patch-chain situation by applying `0.9.7` over a state without the `0.9.6` deploy files, confirming the missing-module risk.
- Built this repair patch with the missing deploy files included.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the patch zip contains:
  - `piTrainer/piTrainer/panels/data/model_deploy_panel.py`
  - `piTrainer/piTrainer/services/data/model_deploy_service.py`
- Verified a fresh patched project reports `0.9.8 / piTrainer_0_9_8`.

## Verification not performed

- Live Windows PySide6 GUI startup was not run in this Linux sandbox.
- Real TensorFlow or TFLite model deployment was not run for this packaging repair.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- Apply this patch over your current v9 folder. It is designed to repair the missing module error even if the deploy files were not already present locally.
