# PATCH NOTES — piTrainer_0_2_0

## Summary

This release rebuilds the PiCar trainer from a Streamlit browser-based workflow into a native **PySide6 desktop application**.
It also restructures the codebase so that:

- each **page** has its own script
- each **panel** inside a page has its own script
- each panel delegates work to separate **sub-functional service scripts**

This matches the requested modular architecture for future expansion and easier maintenance.

---

## Why this patch was made

The earlier trainer relied on Streamlit, which is fast for dashboards but not ideal when the goal is a more traditional desktop application with:

- a native windowed UI
- tighter page/panel organisation
- clearer separation between UI and functional logic
- easier future extension into a full desktop workflow

The request was to move the trainer to **PySide6** and package all needed files into a single deliverable zip.

---

## Main design decisions

### 1) Replace Streamlit with PySide6

**Cause / need**
- Streamlit runs a local web server and opens a browser tab.
- The requested app should behave like a desktop GUI.

**Attempted direction considered**
- Keep Streamlit and just restyle pages.
- This would not satisfy the request for a PySide6 desktop app.

**Final change**
- Rebuilt the trainer around a `QMainWindow` with a `QTabWidget`.
- Added native widgets for path selection, tables, previews, logs, plots, and export controls.

### 2) Enforce page → panel → sub-function structure

**Cause / need**
- The user specifically asked that every page has its own subscripts, each page is made of panels, each panel has its own subscript, and each function has its own sub-functional script.

**Attempted direction considered**
- Use one large script per page with inline helper functions.
- Rejected because it would not meet the requested modular depth.

**Final change**
- `pages/` contains one script per page.
- `panels/` contains one script per panel.
- `services/` contains one script per logical operation used by those panels.

### 3) Keep PiCar dataset compatibility

**Cause / need**
- The trainer should continue to work with the PiCar record layout and tolerant field names.

**Attempted direction considered**
- Simplify the schema to only one strict JSON format.
- Rejected because it would make older or slightly different session dumps harder to use.

**Final change**
- Kept tolerant field matching for steering, throttle, image path, and mode.
- Preserved optional metadata handling for `frame_id`, `session`, camera width/height, and image format.

### 4) Keep training responsive

**Cause / need**
- Training can freeze a GUI if run on the UI thread.

**Attempted direction considered**
- Run training directly from button handlers.
- Rejected because it would block the interface.

**Final change**
- Added a dedicated `QThread`-based training worker.
- Epoch logs, progress, and charts update through Qt signals.

### 5) Support export to `.keras` and `.tflite`

**Cause / need**
- The exported models still need to be usable on the PiCar side.

**Final change**
- Added export services for `.keras` and `.tflite`.
- Added optional INT8 quantization with representative dataset generation.

---

## Final file architecture

```text
piTrainer_0_2_0/
├── main.py
├── README.md
├── requirements.txt
├── run_windows.bat
├── run_linux_mac.sh
├── PATCH_NOTES/
│   └── PATCH_NOTES_piTrainer_0_2_0.md
└── piTrainer/
    ├── app.py
    ├── app_state.py
    ├── main_window.py
    ├── pages/
    │   ├── data_page.py
    │   ├── train_page.py
    │   └── export_page.py
    ├── panels/
    │   ├── common/
    │   ├── data/
    │   ├── train/
    │   └── export/
    ├── services/
    │   ├── data/
    │   ├── train/
    │   └── export/
    ├── ui/
    └── utils/
```

---

## Verification completed

### Static verification
- Checked that the project imports are package-relative and consistent.
- Ran Python compile checks across the generated project files.
- Confirmed the page / panel / service split exists throughout the app structure.

### Functional verification intent covered by code
- Data page can discover sessions under a record root.
- Data page can load JSONL records with tolerant field names.
- Preview panel can show rows and images.
- Train page can split data by session.
- Train page can start training through a background worker.
- Export page can save `.keras` and `.tflite` outputs when TensorFlow is available.

---

## Known limits / notes

1. TensorFlow installation is environment-dependent and is best tested with Python 3.11.
2. Real training/export cannot run unless TensorFlow is installed on the target PC.
3. This release focuses on the desktop trainer architecture and the main training flow, not advanced experiment tracking.

---

## Future improvements

1. Add real-time image augmentation previews.
2. Add training resume / checkpoint support.
3. Add CSV export for metrics.
4. Add embedded validation visualisation for predicted vs actual steering.
5. Add model profile summary panel for parameter count and input/output shapes.
6. Add drag-and-drop dataset folder loading.
7. Add packaged executable builds for Windows.
