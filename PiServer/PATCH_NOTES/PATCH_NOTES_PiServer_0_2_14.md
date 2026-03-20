# PATCH NOTES — PiServer 0_2_14

## Summary
This patch refactors the PiServer dock workspace so the panels are less mixed up and each tab has a clearer job.

The main goal is to separate **read-only status**, **runtime control**, and **saved configuration** so the UI is easier to understand and easier to maintain.

---

## Problems reported
You pointed out two related UI design problems:

1. the current panels were too mixed in function
2. the same panel set was reused across too many tabs, so Manual / Training / Auto did not feel purpose-specific

That made the UI harder to manage and also encouraged save/apply/status bugs because one panel could be acting as control, config, and status at the same time.

---

## Root cause
The old workspace design had two especially mixed panels:

- **Drive + algorithm** mixed runtime setup, algorithm selection, scaling, and model workflow
- **System + config** mixed runtime actions and config persistence

At the same time, the Manual / Training / Auto tabs were mostly using the same panel set with different saved positions, so the tabs did not clearly reflect different workflows.

---

## What changed

### 1) Added a dedicated read-only Telemetry panel
A new **Telemetry** panel now shows:
- current page
- manual command
- applied command
- safety-stop state
- camera backend
- preview state
- motor direction summary
- last update time

This panel is status-only and does not send commands or save config.

### 2) Split the old mixed Drive + algorithm panel into two config panels
The old panel was split into:
- **Runtime tuning**
  - active algorithm
  - max throttle
  - steer mix
- **Model manager**
  - upload model
  - refresh model list
  - choose/load model

This makes runtime tuning and model workflow easier to understand.

### 3) Split the old mixed System + config panel into two clearer roles
The old panel was replaced by:
- **Safety controls**
  - Stop
  - E-Stop
  - Clear
- **Config tools**
  - Save config
  - Reload config
  - update workflow note

This keeps immediate runtime safety controls separate from saved configuration actions.

### 4) Kept Camera settings and Motor settings as config-only panels
The dedicated Camera and Motor tabs now work more cleanly with the new panel model:
- read-only status + preview on one side
- settings/config on the other side
- safety controls kept separate on the Motor tab

### 5) Gave each tab a clearer purpose
The visible panels are now different by tab:

- **Manual** → status, telemetry, preview, runtime tuning, manual drive, safety controls, recording, config tools
- **Training** → status, telemetry, preview, runtime tuning, model manager, recording, config tools
- **Auto** → status, telemetry, preview, runtime tuning, model manager, safety controls, config tools
- **Camera** → status, telemetry, preview, camera settings, config tools
- **Motor** → status, telemetry, preview, motor settings, safety controls, config tools

### 6) Bumped the web asset version to 0_2_14
This forces the browser to request the new HTML/JS/CSS files instead of reusing stale cached assets.

---

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_14.md`

---

## Verification
I checked the patch for the following:
- every `document.getElementById(...)` reference in `app.js` still exists in the new HTML
- updated `app.js` passes `node --check`
- PiServer Python tests still pass with `python3 -m unittest discover -s tests -q`
- `piserver/app.py` still compiles with `python3 -m py_compile`
- tab panel visibility now follows the new page-specific panel sets
- status updates now populate both the compact Status panel and the read-only Telemetry panel

---

## How to apply
1. copy the patched files into your existing `PiServer` folder
2. restart PiServer
3. hard-refresh the browser once
4. open each tab and confirm the new panel split/layout is loaded

---

## Expected result after this patch
The workspace should now feel much cleaner:
- fewer mixed-purpose panels
- clearer difference between Manual / Training / Auto / Camera / Motor
- easier maintenance because control, config, and read-only status are more clearly separated

This patch mainly fixes the **UI architecture problem** we discussed. It does not remove your existing routes or runtime features; it reorganizes them into more suitable panels.
