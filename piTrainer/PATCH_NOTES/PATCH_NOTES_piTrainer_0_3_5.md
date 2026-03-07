# PATCH NOTES — piTrainer_0_3_5

## Summary
Added a new **Validation** tab so you can verify a trained model against your dataset inside the trainer.

## Included files
- `piTrainer/main_window.py`
- `piTrainer/pages/validation_page.py`
- `piTrainer/panels/validation/__init__.py`
- `piTrainer/panels/validation/validation_summary_panel.py`
- `piTrainer/panels/validation/validation_config_panel.py`
- `piTrainer/panels/validation/validation_actions_panel.py`
- `piTrainer/panels/validation/validation_plot_panel.py`
- `piTrainer/services/validation/__init__.py`
- `piTrainer/services/validation/validation_service.py`

## Added
- New **Validation** tab between **Train** and **Export**
- Validation Summary panel
- Validation Config panel
- Validation Actions panel
- Validation Plot panel
- Validation Log panel
- `Ctrl+5` shortcut for the new tab

## Validation features
- Validate the **current trained in-memory model**
- Or load a saved **`.keras` / `.h5`** model file
- Choose validation source:
  - Validation split
  - Current filtered rows
  - Training split
- Set validation batch size
- Optionally limit max rows for a faster check

## Output
- Steering MAE / RMSE / Bias
- Speed MAE / RMSE / Bias
- Prediction vs Ground Truth plot
- Prediction Error Histogram
- Sample Prediction Trace
- Validation log output

## Notes
- This validation path expects a Keras model with steering + throttle outputs, matching the trainer model format.
- The feature loads and preprocesses images using the current training image size from the app state.
- Original dataset files are not changed by validation.

## Checks performed
- Python compile check passed on all patched files
- Validation service sanity-checked with a fake prediction model and temporary sample images
- Packaged as patch-only zip with the same wrapper-folder style: `piTrainer_0_3_5/...`
