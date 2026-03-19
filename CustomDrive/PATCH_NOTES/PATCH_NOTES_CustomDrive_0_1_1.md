# PATCH NOTES — CustomDrive 0_1_1

## Summary

This patch separates **launch/run settings** from the existing hardware/runtime tuning settings and makes both launch paths use the same saved file.

After this patch, CustomDrive has two clear launch modes:

1. **GUI mode**
2. **Headless mode**

Both launch modes now read the same saved run settings file.

---

## Problem

The previous patch already had simulation/live runtime backends and a web GUI, but the project still had two practical gaps:

1. there was no dedicated shared file for **run defaults** such as backend mode, cycle count, and launch tick speeds
2. the GUI did not provide a clear screen for editing and saving those run defaults for later reuse by the headless runner

That made repeated testing more manual and made it easy for GUI mode and headless mode to drift apart.

---

## Changes made

### 1) Added a dedicated shared run settings file

Added:

- `CustomDrive/config/run_settings.json`
- `CustomDrive/custom_drive/run_settings.py`

This new file stores launch/run defaults only:

- `runtime_mode`
- `max_cycles`
- `headless_tick_s`
- `gui_tick_s`
- `auto_start_gui`

This keeps launch behavior separate from the existing `runtime_settings.json`, which still handles camera, motor, steering-mix, and perception tuning.

### 2) Updated headless launcher to use the shared run settings file

Updated:

- `CustomDrive/run_custom_drive_demo.py`

Now the headless runner:

- defaults to `config/run_settings.json`
- still allows CLI overrides when needed
- clearly reports that it is running in **headless** launch mode

### 3) Updated GUI launcher to use the shared run settings file

Updated:

- `CustomDrive/run_custom_drive_web.py`

Now the GUI launcher defaults to the same saved run settings file before starting the web app.

### 4) Added explicit alias launchers for clarity

Added:

- `CustomDrive/run_custom_drive_headless.py`
- `CustomDrive/run_custom_drive_gui.py`

These make the two launch paths obvious without removing backward compatibility.

### 5) Added GUI controls for saving run settings

Updated:

- `CustomDrive/custom_drive/web_app.py`
- `CustomDrive/custom_drive/web/templates/index.html`
- `CustomDrive/custom_drive/web/static/app.js`
- `CustomDrive/custom_drive/web/static/styles.css`

The GUI now includes a **Saved Run Settings** panel where you can:

- choose `sim` or `live`
- set default max cycles
- set headless tick delay
- set GUI tick delay
- choose whether the GUI should auto-start the mission
- save those settings back to `config/run_settings.json`

The GUI also rebuilds the active runtime after saving so the current session matches the saved run defaults more closely.

### 6) Updated README

Updated:

- `CustomDrive/README.md`

The documentation now clearly explains:

- the two launch modes
- the shared run settings file
- compatibility launchers
- how run settings and runtime settings are separated

---

## Verification performed

### Verified

- `python -m compileall CustomDrive`
- `python run_custom_drive_demo.py --mode sim --cycles 1 --tick 0.02` starts the headless launcher and prints mission state transitions correctly
- `load_run_settings()` reads the new shared run settings file correctly

### Not fully runtime-verified in this container

- full Flask GUI endpoint execution was not run end-to-end here because the container environment did not have Flask installed
- Raspberry Pi live hardware behavior still depends on the target Pi having the required runtime packages and hardware available

---

## Notes

- `runtime_settings.json` is still the correct place for camera, motor, and perception tuning
- `run_settings.json` is now the correct place for saved launch defaults used by both GUI mode and headless mode
- the old launcher names still work, but the new alias launchers make the two modes easier to understand

---

## Files changed in this patch

### New files

- `CustomDrive/config/run_settings.json`
- `CustomDrive/custom_drive/run_settings.py`
- `CustomDrive/run_custom_drive_headless.py`
- `CustomDrive/run_custom_drive_gui.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_1.md`

### Updated files

- `CustomDrive/README.md`
- `CustomDrive/custom_drive/web_app.py`
- `CustomDrive/custom_drive/web/templates/index.html`
- `CustomDrive/custom_drive/web/static/app.js`
- `CustomDrive/custom_drive/web/static/styles.css`
- `CustomDrive/run_custom_drive_demo.py`
- `CustomDrive/run_custom_drive_web.py`
