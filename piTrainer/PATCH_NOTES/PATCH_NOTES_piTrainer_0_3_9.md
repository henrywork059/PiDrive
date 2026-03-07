# PATCH NOTES — piTrainer_0_3_9

## Summary
Small runtime fix for the Train tab epoch review panel.

## Cause
The new epoch review UI tried to clear the preview image with `QLabel.setPixmap(None)`.
PySide6 does not accept `None` for `setPixmap`, so training crashed before the first epoch review cleared.

## Fix
- Replaced `setPixmap(None)` with `clear()` in `train_epoch_review_panel.py`
- Applied the same fix for the missing-image fallback path

## Result
- Starting training no longer crashes at `clear_review()`
- Epoch best/worst frame cards can reset safely before training begins

## Notes
The `QWindowsWindow::setGeometry` message is only a Qt window-size warning and is not the cause of the crash.
