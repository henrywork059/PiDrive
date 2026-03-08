# PATCH NOTES — piTrainer_0_3_12

## What changed

This patch fixes the Train epoch-review preview details and expands Validation so you can inspect validated frames directly with overlay comparison.

### 1) Train epoch-review cards now show frame ID and frame number more clearly
- Added **Frame ID** and **Frame No.** text to the best-fit / worst-fit cards.
- Added **Review frame N / total** so it is easier to tell which sampled frame you are looking at.
- Added safer fallback logic when a dataset row does not already carry an explicit frame-number field.

### 2) Train epoch-review preview now overlays target vs predicted paths
- The epoch-review image cards now draw:
  - **Target / trained path**
  - **Predicted path**
- This makes the best-fit / worst-fit examples much easier to inspect than raw numbers alone.

### 3) Validation tab can now browse frames with overlay comparison
- Added a new **Validation Frame Review** panel.
- The panel shows a selectable table of validated rows.
- Selecting a row displays the frame image with:
  - **Target / trained path overlay**
  - **Predicted path overlay**
- The preview also shows row/session/frame info and the numeric target/predicted steering + speed values.

### 4) Validation results now keep the metadata needed for frame review
- Validation results now store:
  - image paths
  - session names
  - frame IDs
  - frame numbers
  - combined error
- This enables the new Validation frame browser and keeps row identification clearer.

## Files changed
- `piTrainer/services/data/overlay_service.py`
- `piTrainer/services/train/worker.py`
- `piTrainer/panels/train/train_epoch_review_panel.py`
- `piTrainer/services/validation/validation_service.py`
- `piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/pages/validation_page.py`

## Checks performed
- Python compile check passed on all patched files.
- Validation preview-row helper was sanity-tested with sample result data.
- Checked that the new Validation frame-review panel avoids the earlier `setPixmap(None)` crash pattern.

## Notes
- This is a **patch-only** zip.
- Foldering follows the same wrapper-folder patch style as recent trainer patches.
- Original datasets are not modified by this patch.
