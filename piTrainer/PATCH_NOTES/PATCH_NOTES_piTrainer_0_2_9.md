# PATCH NOTES — piTrainer_0_2_9

## Scope
Patch-only update for the Data page. This patch adds live frame overlays and a new data plot panel while keeping the same project-relative folder structure for manual patching.

## What was added

### 1) Overlay Controls panel
A new **Overlay Controls** panel was added to the Data page.

It lets you toggle these overlays on the current preview frame:
- **Speed as vertical bar**
- **Steering as horizontal bar** with **0 in the middle**
- **Steering as semi-circle bar** with **0 in the middle**

### 2) Live overlay rendering on Image Preview
The Image Preview panel now stores the currently selected record and redraws the preview whenever:
- the selected frame changes, or
- overlay options are toggled.

This means overlays update immediately without needing to reload the dataset.

### 3) Data Plot panel
A new **Data Plot** panel was added to the Data page.

It shows:
- a session selector
- a plot of **steering** and **speed/throttle** across frame index
- summary statistics for the currently plotted frames

The plot follows the current filtered preview dataframe, so if you filter the dataset, the plot updates too.

## Structural changes

### Updated files
- `piTrainer/pages/data_page.py`
- `piTrainer/panels/data/preview_panel.py`
- `piTrainer/panels/data/image_preview_panel.py`

### New files
- `piTrainer/panels/data/overlay_control_panel.py`
- `piTrainer/panels/data/data_plot_panel.py`
- `piTrainer/services/data/overlay_service.py`
- `piTrainer/services/data/plot_service.py`

## Default Data page layout
The Data page dock layout was expanded to include:
- Overlay Controls on the left stack
- Data Plot on the right stack

## Verification performed
- Python compile check on all patched files
- sanity check on plot summary helper logic using sample dataframe input
- constructor/callback wiring checked for Data page, Preview panel, Image Preview panel, Overlay panel, and Data Plot panel

## Notes
- This patch is delivered as **patched files only**.
- Paths are kept in the same project-relative structure for direct overwrite into your existing trainer folder.
- Full live GUI behavior could not be visually exercised in this environment, so this is code-checked and wiring-checked rather than fully GUI-runtime verified.
