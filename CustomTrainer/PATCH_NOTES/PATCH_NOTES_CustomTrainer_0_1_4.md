# PATCH NOTES — CustomTrainer 0_1_4

## Summary
This patch fixes a Windows log-stream decoding crash seen when running training from the PySide6 UI on Traditional Chinese Windows systems using the CP950 code page.

## Reported issue
Training could abort almost immediately with an error similar to:

```text
[error] 'cp950' codec can't decode byte 0xe2 in position ...
```

This happened while the UI was reading subprocess output from the internal Ultralytics runner.

## Root cause
The PySide6 command worker launched the training subprocess with `text=True` and no explicit encoding.
On Windows, Python then decoded stdout using the system locale, which can be CP950.
Ultralytics and its dependencies may emit UTF-8 bytes or mixed Unicode-heavy console output, causing decode failures in the parent UI process.

## Changes made

### 1) Hardened subprocess log reading
File changed:
- `custom_trainer/ui/qt_helpers.py`

Changes:
- switched subprocess stdout reading from text mode to raw bytes mode
- added safe per-line decoding with fallback order:
  - UTF-8
  - preferred system encoding
  - CP950
  - final UTF-8 with replacement
- kept live line-by-line log streaming in the UI

### 2) Forced safer child process stdio configuration
File changed:
- `custom_trainer/services/ultralytics_cli.py`

Changes:
- reconfigure child `stdout` and `stderr` to UTF-8 with replacement when supported
- helps make emitted training logs more consistent across Windows environments

## Expected result
- Training, validation, and export logs should continue streaming in the docked log panel
- CP950 decode crashes should no longer terminate the command worker
- Unicode characters that cannot be represented exactly will be replaced safely instead of crashing the UI

## Verification performed
- syntax check passed for patched Python files
- byte-decoding fallback behavior reviewed against UTF-8 and CP950-style output patterns

## Files included in this patch zip
- `CustomTrainer/custom_trainer/ui/qt_helpers.py`
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_4.md`

## Notes
This patch only addresses the Windows console decoding failure.
If training later fails for dataset, model, or Ultralytics reasons, those should now appear normally in the UI log panel instead of being hidden by the codec crash.
