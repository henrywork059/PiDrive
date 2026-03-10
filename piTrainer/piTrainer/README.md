# piTrainer 0_3_18 README Note

This `0_3_18` package is a **patch-only** layout refresh.

## What this patch changes
- Reorganizes the **default** panel sizes and dock positions across the main pages.
- Makes the main working panels open larger by default.
- Makes logs and secondary helper panels open smaller by default.
- Adds a shared dock-clearing helper in `DockPage` so layout rebuilds are cleaner.

## Files included in this patch
- `piTrainer/pages/dock_page.py`
- `piTrainer/pages/data_page.py`
- `piTrainer/pages/preprocess_page.py`
- `piTrainer/pages/train_page.py`
- `piTrainer/pages/validation_page.py`
- `piTrainer/pages/export_page.py`
- `piTrainer/README.md`
- `PATCH_NOTES/PATCH_NOTES_piTrainer_0_3_18.md`

## Important note about saved layouts
If you already have a saved/custom dock layout from an older run, the new default layout may not fully appear until you reset your saved layout state.

## Packaging
- Patch-only zip
- Same wrapper-folder style
- Same relative project paths
