# piTrainer Windows EXE packaging

This packaging setup is designed for:

- easy loading: one-folder app, no one-file extraction delay;
- smaller launcher EXE: heavy libraries stay beside the EXE instead of being packed into one huge file;
- easier debugging: the app folder can be opened and inspected if a DLL or data file is missing.

Use this instead of `--onefile` for piTrainer. TensorFlow, PySide6, matplotlib, pandas and numpy are large, so a true tiny single EXE is not realistic without removing training/export features.

## Recommended build type

Use PyInstaller one-folder mode:

```powershell
cd C:\Users\henry_sik0ar\Downloads\PiTrainer\PiDrive\piTrainer
..\..\.venv\Scripts\Activate.ps1   # adjust if your venv is in a different folder
powershell -ExecutionPolicy Bypass -File .\PACKAGING\build_windows_onedir.ps1
```

The output will be:

```text
dist_exe\PiTrainer\PiTrainer.exe
dist_exe\PiTrainer\Run_PiTrainer.bat
dist_exe\PiTrainer_win_onedir.zip
```

Open the app with:

```text
dist_exe\PiTrainer\PiTrainer.exe
```

For copying to another Windows PC, send/copy:

```text
dist_exe\PiTrainer_win_onedir.zip
```

Then unzip it and run `PiTrainer.exe`.

## Why not one-file?

`--onefile` looks tidy, but it is not ideal here:

- it extracts TensorFlow/PySide DLLs to a temporary folder every time;
- startup is slower;
- antivirus scanning is more likely to slow it down;
- the single EXE becomes very large;
- debugging missing files is harder.

One-folder mode starts faster and keeps the main EXE small, even though the whole app folder still contains large runtime libraries.

## Smaller build tips

The provided spec already excludes common unused packages such as Jupyter, pytest, tkinter, torch, OpenCV and test packages.

To keep the build smaller:

1. Build from a clean venv used only for piTrainer.
2. Do not install unrelated packages in that venv.
3. Use the provided one-folder spec, not `--onefile`.
4. Zip the output folder for transfer.
5. Do not enable UPX for this project; TensorFlow/PySide DLLs are safer uncompressed.


## If zip creation says a file is locked

PyInstaller may finish the app folder before Windows, File Explorer, or antivirus releases every file. If `Compress-Archive` reports that `_internal\base_library.zip` or another build file is being used by another process, the app folder is already usable:

```text
dist_exe\PiTrainer\PiTrainer.exe
```

The build script retries zip creation automatically. If the zip still cannot be made, close any Explorer window opened inside `dist_exe`, wait a few seconds, and rerun the build script. You can also copy the whole `dist_exe\PiTrainer` folder directly without using the zip.

## Console build for debugging

For a console window during debugging:

```powershell
powershell -ExecutionPolicy Bypass -File .\PACKAGING\build_windows_onedir.ps1 -Console
```

For the normal user-facing build, omit `-Console`.

## Version gate config

The spec includes `config/version_gate.json` when it exists. Frozen builds also support an external config beside the EXE:

```text
dist_exe\PiTrainer\config\version_gate.json
```

If the version gate is enabled, make sure the online manifest allows the current app version before distributing the EXE.

## Expected size

Because piTrainer includes TensorFlow and PySide6, the unzipped folder can still be large. The goal of this setup is not a tiny app; the goal is a smaller launcher, faster startup, and fewer one-file extraction problems.
