# PATCH NOTES — piTrainer_0_2_7

## Scope
Patch-only update. This zip contains only the files changed for this patch, with the same relative folder paths as the main project.

## Changes

### 1) Main content is now dockable
- Removed the fixed central main-content dependency from the page layouts.
- The main content on each page is now a normal dock panel:
  - Data page: `Record Preview`
  - Train page: `Training History`
  - Export page: `Export Log`
- This allows the main content to be moved and redocked more freely.

### 2) Data page presentation improved
- Rebalanced the default Data page layout so it opens in a cleaner 3-column dock arrangement:
  - left: root / sessions / filter / actions / data control
  - middle: record preview
  - right: image preview / dataset stats
- Renamed the actions dock title from `Quick Actions` to `Data Actions` in the default page layout.

### 3) Numeric frame filters added
- Added speed-range filtering and steering-range filtering to the Data page filter panel.
- Speed filtering uses the loaded `throttle` values as the numeric speed field.
- Each numeric range can be enabled or disabled independently.
- Existing text and mode filters are retained.

### 4) Session checkbox presentation improved further
- Reworked the session list rows so the checkbox indicator and session label are separate widgets.
- This avoids the checkbox indicator overlaying the text.
- Added row click toggling so the session row is easier to use.

### 5) UI size adjustments
- Reduced dock title bar height by about 10%.
- Reduced button height and padding by about 10%.

## Files changed
- `piTrainer/pages/dock_page.py`
- `piTrainer/pages/data_page.py`
- `piTrainer/pages/train_page.py`
- `piTrainer/pages/export_page.py`
- `piTrainer/panels/data/session_list_panel.py`
- `piTrainer/panels/data/frame_filter_panel.py`
- `piTrainer/services/data/filter_service.py`
- `piTrainer/ui/styles.py`
- `PATCH_NOTES/PATCH_NOTES_piTrainer_0_2_7.md`

## Checks performed
- Python compile check passed for all patched files.
- Filter service behavior was tested with sample data for:
  - text filter
  - mode filter
  - speed range filter
  - steering range filter
  - combined filters
- Fixed an initialization bug risk where the filter panel could try to auto-apply before the Data page finished constructing the preview panel.

## Notes
- This patch was packaged as patch-only, not a full project copy.
- I did not run a live PySide6 GUI session in this environment, so runtime behavior inside your desktop environment should still be tested after applying the patch files over your current project.
