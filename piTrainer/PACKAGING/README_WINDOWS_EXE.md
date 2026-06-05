# piTrainer Windows EXE packaging

## Packaging strategy

Use the reliability-first one-folder build. Do not try to shrink the package by excluding Python standard-library modules, TensorFlow/Keras internals, or Matplotlib internals. TensorFlow and Keras are the large part of this app, and Keras imports several training modules dynamically only when training starts. A smaller EXE folder is not useful if the app opens but fails at Start Training.

Expected result:

- The app folder may be large.
- `PiTrainer.exe` stays small because runtime files are beside it in `_internal`.
- Startup is faster and more reliable than `--onefile`.
- Training should use the same installed environment dependencies that PyInstaller can collect.


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

## Size expectation and safe build tips

Do not reduce size by excluding standard-library modules or TensorFlow/Keras training modules. Previous aggressive exclusions made the EXE open but fail during startup or training. TensorFlow/Keras are the large part of this project, so a very small build is not realistic while keeping training/export features.

Safe tips:

1. Build from the current piTrainer venv that already runs `python main.py`.
2. Avoid installing unrelated packages in that venv before packaging.
3. Use the provided one-folder spec, not `--onefile`.
4. Zip the output folder for transfer.
5. Do not enable UPX for this project; TensorFlow/PySide DLLs are safer uncompressed.


## If the EXE says `No module named unittest`

This means an older packaging spec excluded Python's standard-library `unittest` package too aggressively. Matplotlib imports `pyparsing`, and `pyparsing.testing` imports `unittest` during startup, so the frozen app needs `unittest` even though piTrainer does not use unit tests directly.

Apply patch `0.8.12` or later, then rebuild the one-folder EXE.


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


## Training starts in Python but fails in the EXE

The frozen EXE needs the TensorFlow/Keras training backend modules included at
build time. The packaging spec now pins the Keras backend to TensorFlow and adds
the dynamic Keras/TensorFlow modules used by the Train page. Rebuild after
applying this patch.

For a more detailed runtime traceback, build a console copy:

```powershell
powershell -ExecutionPolicy Bypass -File .\PACKAGING\build_windows_onedir.ps1 -Console
.\dist_exe\PiTrainer\PiTrainer.exe
```

If training still fails, copy the Train page log and the console traceback.