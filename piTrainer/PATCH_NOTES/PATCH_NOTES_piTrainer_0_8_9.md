# piTrainer 0.8.9 Patch Notes — Windows one-folder EXE packaging helper

## Request summary

Add a packaging setup to build piTrainer as an EXE that is easy to load and avoids an unnecessarily huge one-file executable.

## Cause / reason

piTrainer depends on PySide6, TensorFlow, matplotlib, pandas and numpy. These libraries are large and contain many DLL/data files. A PyInstaller `--onefile` build would make a very large executable and can start slowly because it extracts the runtime files to a temporary folder each time.

A one-folder build is better for piTrainer:

- faster startup;
- smaller main `.exe` launcher;
- easier file loading;
- easier debugging;
- the app folder can be zipped for copying to another Windows PC.

## Files changed / added

- `piTrainer/PACKAGING/piTrainer_onedir.spec`
- `piTrainer/PACKAGING/build_windows_onedir.ps1`
- `piTrainer/PACKAGING/README_WINDOWS_EXE.md`
- `piTrainer/piTrainer/version.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_9.md`

## Exact behavior changed

- Adds a PyInstaller one-folder spec for piTrainer.
- Adds a PowerShell build script for Windows.
- The build output goes to:
  - `dist_exe/PiTrainer/PiTrainer.exe`
  - `dist_exe/PiTrainer/Run_PiTrainer.bat`
  - `dist_exe/PiTrainer_win_onedir.zip`
- The spec includes `config/version_gate.json` when present.
- The spec excludes common unused packages such as Jupyter, pytest, tkinter, torch, OpenCV and test packages to reduce avoidable build size.
- The app version constant is updated to `0.8.9 / piTrainer_0_8_9`.

## Behavior intentionally not changed

- No training logic changed.
- No validation logic changed.
- No export logic changed.
- No TFLite output logic changed.
- No UI layout behavior changed.
- No runtime/user settings are reset.
- The EXE helper is additive and does not remove the normal `python main.py` workflow.

## Rollback-risk check

This patch is intended to apply after the accepted v8 patch line. It preserves the six-step workflow title from the Export Validation patches:

```text
Data → Preprocess → Train → Validate → Export → Export Validation
```

It does not replace existing runtime modules or patch core app files except the version constants.

## Verification actually performed

- Inspected the current `piTrainer_0_8_0.zip` structure and the existing entry point `piTrainer/main.py`.
- Confirmed the version-gate loader supports bundled or side-by-side `config/version_gate.json` for frozen builds.
- Syntax-checked the new PyInstaller spec as Python.
- Ran Python compilation on the patched `version.py`.
- Checked the patch zip contains only packaging files, version constants, and this patch note.

## Verification not performed

- A real Windows EXE build was not run in this sandbox because Windows/PyInstaller/TensorFlow runtime packaging is environment-specific.
- Live PySide6 GUI launch from the frozen EXE was not tested here.
- Size measurements were not taken here.

## How to use

From PowerShell in the `piTrainer` component folder:

```powershell
cd C:\Users\henry_sik0ar\Downloads\PiTrainer\PiDrive\piTrainer
..\..\.venv\Scripts\Activate.ps1
powershell -ExecutionPolicy Bypass -File .\PACKAGING\build_windows_onedir.ps1
```

Then run:

```text
dist_exe\PiTrainer\PiTrainer.exe
```
