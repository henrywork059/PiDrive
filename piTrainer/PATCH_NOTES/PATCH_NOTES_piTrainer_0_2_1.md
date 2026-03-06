# PATCH NOTES — piTrainer_0_2_1

## Summary

This patch updates the PySide6 trainer so the desktop GUI now launches in **dark mode by default**.

## What changed

### 1) Global dark theme stylesheet
- Replaced the light stylesheet with a dark palette.
- Updated main window, group boxes, tabs, buttons, input fields, lists, tables, progress bars, and status bar.
- Added darker surfaces plus readable text and selection colors.

### 2) Force a consistent Qt widget style
- The app now prefers the Qt **Fusion** style when available.
- This helps the dark theme render more consistently across platforms.

### 3) Dark mode for training charts
- Updated the Matplotlib training-history panel to use dark backgrounds, light axis labels, dark grid lines, and a dark legend.
- This prevents the chart area from staying bright while the rest of the app is dark.

## Files changed
- `piTrainer/app.py`
- `piTrainer/ui/styles.py`
- `piTrainer/panels/train/train_history_panel.py`
- `README.md`

## Result

The trainer now opens as a native **dark-themed** PySide6 desktop app without needing any manual theme switch.
