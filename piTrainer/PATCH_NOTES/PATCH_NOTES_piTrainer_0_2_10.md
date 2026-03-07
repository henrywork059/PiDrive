# PATCH NOTES — piTrainer_0_2_10

## Scope
Patch-only update for the Data page. This patch moves playback controls into their own dedicated panel and expands the Data Plot panel with multiple more-useful plot modes.

## What changed

### 1) New Playback Control panel
Playback controls are no longer embedded inside **Record Preview**.

A new **Playback Control** panel was added with:
- **Play**
- **Stop**
- **Restart**
- **Playback speed** control in frames per second
- current playback status / frame position readout

This makes frame playback easier to control without mixing transport controls into the preview table.

### 2) Record Preview panel cleaned up
The **Record Preview** panel now focuses on:
- frame list table
- current frame summary
- selection handling
- playback timer logic under the hood

The visible autoplay button was removed from that panel.

### 3) Data Plot panel expanded
The **Data Plot** panel now supports multiple plot modes:
- **Steering + Speed Timeline**
- **Steering Histogram**
- **Speed Histogram**
- **Steering vs Speed Scatter**
- **Mode Distribution**
- **Session Frame Count**

This gives a more useful view of session behavior, value spread, and dataset balance.

## Structural changes

### Updated files
- `piTrainer/pages/data_page.py`
- `piTrainer/panels/data/preview_panel.py`
- `piTrainer/panels/data/data_plot_panel.py`
- `piTrainer/services/data/plot_service.py`

### New files
- `piTrainer/panels/data/playback_control_panel.py`

## Verification performed
- Python compile check on all patched files
- search check to confirm old autoplay callback path was removed
- sample-data sanity check for plot summary and session filtering helpers
- Data page callback wiring checked for the new playback panel

## Notes
- This patch is delivered as **patched files only**.
- Paths are kept in the same project-relative structure for direct overwrite into your existing trainer folder.
- Full live GUI behavior could not be visually exercised in this environment, so this is code-checked and wiring-checked rather than fully GUI-runtime verified.
