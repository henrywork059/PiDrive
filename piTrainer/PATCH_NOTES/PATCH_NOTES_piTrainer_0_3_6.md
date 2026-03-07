# PATCH NOTES — piTrainer_0_3_6

## What changed
- Updated `README.md` so it no longer reports the old `piTrainer_0_2_4` version.
- Expanded the **Preprocess** tab so it can synthesize more training data instead of only filtering rows.
- Added deterministic balancing for overly common near-zero steering rows.
- Added mirrored-row generation for left-right image flips.
- Added deterministic color-variation row generation.
- Updated the training dataset loader so these synthetic preprocess rows are actually applied during training.
- Improved preprocess summary/preview text to report kept rows vs generated rows.

## New preprocess options
- **Balance near-zero steering rows**
  - reduces the overrepresented straight-driving samples that often dominate PiCar datasets
  - uses a deterministic keep ratio instead of random dropping
  - helps the model pay more attention to turning examples

- **Add one left-right mirrored copy per row**
  - creates an extra training row
  - flips the image horizontally during training
  - negates steering so the label matches the mirrored image
- **Color variants per row**
  - creates additional synthetic rows with deterministic brightness / contrast / saturation / hue changes
  - speed and steering labels stay the same

## Files changed
- `README.md`
- `piTrainer/pages/preprocess_page.py`
- `piTrainer/panels/preprocess/preprocess_config_panel.py`
- `piTrainer/panels/preprocess/preprocess_summary_panel.py`
- `piTrainer/services/preprocess/preprocess_service.py`
- `piTrainer/services/train/dataset_service.py`

## Verification
- Python compile check passed on all patched files.
- Preprocess service was sanity-tested with sample rows and real image paths.
- Straight-row balancing was verified to keep turning rows while reducing near-zero steering rows.
- Mirrored rows were verified to invert steering labels.
- Color-variant rows were verified to carry deterministic augmentation metadata.
- Training dataset loader was reviewed to ensure it consumes the new augmentation metadata columns.

## Notes
- This patch only changes the active in-memory training dataset flow.
- Source images and original `records.jsonl` files are not overwritten by preprocess synthesis.
