# PiTrainer 0_3_8 Patch Notes

## Scope
This patch focuses on the Preprocess and Train tabs.

## What changed

### Preprocess tab
- Split preprocess controls into two separate panels:
  - `Preprocess Filters`
  - `Preprocess Recipe`
- Added a clearer action flow:
  - Preview Preprocess
  - Confirm and Start Preprocess
  - Reset Preprocess
  - Save Preprocess Settings
  - Save Preprocessed Data
  - Sync Image Size to Train Tab
- Mild color variants are now intentionally limited to small exposure and white-balance style shifts instead of strong recoloring.
- Added save/load support for preprocess settings at the default trainer output folder.
- Added save support for active preprocessed data to a timestamped dataset folder containing:
  - `preprocessed_records.csv`
  - `preprocessed_records.jsonl`
  - `preprocess_recipe.json`
- Confirming preprocessing still updates the active training dataframe immediately, so the Train tab automatically uses the active preprocessed data.

### Train tab
- Added more training settings:
  - split mode: By session / Random rows / Sequential rows
  - dropout rate
  - steering loss weight
  - speed loss weight
- Single-session projects can now still create train/validation splits by rows when the split mode is not session-based.
- Added `Save Trained Model` directly on the Train tab.
- Saving a trained model now also auto-fills the Validation tab with that saved model path.
- Added a new `Epoch Frame Review` panel that shows the current best-fit and worst-fit sample frames every epoch during training.

## Important implementation notes
- Saved preprocess data stores the active preprocessed dataframe and recipe metadata. It does not overwrite original session files.
- The epoch frame review uses a small review sample from the training dataframe to avoid very heavy per-epoch overhead.

## Verification
- Python compile check passed on all patched Python files.
- Preprocess save/load flow was sanity-tested with temporary images and sample rows.
- Split logic was sanity-tested for Random rows and Sequential rows.

## Honest note
- The code was not fully live-run as a desktop PySide6 + TensorFlow session in this container, so this patch is syntax-checked and logic-checked rather than fully GUI-runtime proven here.
