# PATCH NOTES — piTrainer_0_3_7

## Goal
Add more useful functions to **Preprocessing** and **Training** without changing the project layout or switching back to a full baseline package.

---

## What was added

### 1) Preprocessing improvements
The Preprocess tab now supports several additional controls that are useful for real driving datasets:

- **Drop duplicate image paths**
  - Helps remove repeated rows that point to the same source frame.
  - Useful after session merges or manual edits.

- **Frame stride / keep every Nth row**
  - Lets you thin very dense recordings.
  - Reduces near-duplicate consecutive frames.

- **Turn-example boost**
  - Duplicates rows with strong steering values above a threshold.
  - Helps reduce the common “mostly-straight-driving” bias.

These work together with the existing preprocess features:
- mode filtering
- steering/speed range filtering
- require existing images
- near-zero steering balancing
- mirror synthesis
- color-variant synthesis
- image-size sync to training

### 2) Training improvements
The Train tab now supports several additional controls:

- **Model size**
  - `Small CNN`
  - `Medium CNN`

- **Random seed**
  - Makes train/validation behavior more repeatable.

- **Early stopping**
  - Stops training when the chosen loss stops improving.
  - Restores best weights.

- **Reduce learning rate on plateau**
  - Automatically lowers the learning rate when training stalls.

---

## Files changed

- `piTrainer/app_state.py`
- `piTrainer/panels/preprocess/preprocess_config_panel.py`
- `piTrainer/panels/preprocess/preprocess_summary_panel.py`
- `piTrainer/services/preprocess/preprocess_service.py`
- `piTrainer/panels/train/train_config_panel.py`
- `piTrainer/services/train/model_service.py`
- `piTrainer/services/train/worker.py`

---

## Implementation notes

### Preprocessing pipeline order
The preprocessing service now applies steps in this order:
1. mode / range / image-exists filters
2. duplicate-image removal (optional)
3. frame stride sampling (optional)
4. near-zero steering balance (optional)
5. turn-example boost (optional)
6. mirror / color synthetic expansion (optional)

### Turn-example boost
- Uses absolute steering magnitude.
- Rows above the threshold are duplicated by the configured extra-copy count.
- Boosted rows are marked with augmentation metadata so they can be counted in summaries.

### Training callbacks
The training worker now optionally adds:
- `EarlyStopping`
- `ReduceLROnPlateau`

Monitoring uses:
- `val_loss` when validation data exists
- `loss` otherwise

### Model size
Added a second model architecture:
- `Small CNN` = existing lighter model
- `Medium CNN` = deeper and slightly wider model for more capacity

---

## Verification performed

### Code checks
- Python compile check passed for all patched Python files.
- Preprocess service sanity-tested with temporary sample images and sample rows.

### What was specifically tested
- duplicate-image removal count
- frame-stride sampling flow
- turn-example boosting count
- mirror/color synthetic count consistency
- summary dictionary row totals vs output dataframe length

---

## Known limits
- I did **not** fully live-run the PySide6 desktop GUI in this container.
- I did **not** run a full TensorFlow training cycle in this environment.
- So this patch is **syntax-checked and logic-checked**, but not fully desktop-runtime proven here.

---

## Packaging
This patch zip contains **only changed files** and keeps the same wrapper-folder patch style and same relative project paths.
