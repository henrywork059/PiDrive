# PiCar Patch Notes — piCar_0_2_10

Date: 2026-03-05

## Goals
1) Fix **Status** panel sometimes expanding to **2 grid rows**.
2) Make **FPS** display more realistic/stable.
3) **Remove Speed bar** (slider) from Manual panel.
4) Add **Download Recording (ZIP)** feature:
   - Dropdown to choose a recording session
   - Button next to **Toggle Rec** to download a zipped session

---

## 1) Status bar taking 2 rows
### Cause
CSS Grid tracks defined as `repeat(rows, 1fr)` have an implicit minimum size of `auto` (min-content). If a panel’s content becomes taller than the track, the grid can expand that row to fit content, making it look like the Status panel occupies 2 rows.

### Attempted fixes
- Reduced padding and hid the Status title (helped but did not guarantee fixed height).

### Final fix
- Changed grid rows to **fixed shrinkable tracks**:
  - `grid-template-rows: repeat(var(--rows), minmax(0, 1fr));`
  - `grid-auto-rows: minmax(0, 1fr);`
- Added `overflow: hidden` on `.panel` so content can’t force track growth.

### Verification
- Open UI on phone + desktop.
- Shrink browser window height.
- Confirm Status stays 1 row and its text scrolls horizontally (swipe/drag).

---

## 2) FPS display “not real”
### Cause
The previous FPS calculation used a 1-second bucket counter in the MJPEG generator. On real networks/browsers, that approach can look jumpy or misleading due to buffering and irregular frame delivery.

### Final fix
- Replaced bucket FPS with an **exponential moving average (EMA)** of instantaneous FPS (`1/dt`) between frames.
- This produces a smoother and more believable FPS reading.

### Verification
- Load `/` (with video active).
- Watch FPS in Status while changing network load / device.
- Confirm FPS stabilizes instead of jumping wildly.

---

## 3) Remove the Speed bar
### Cause
Manual panel had a speed slider duplicating the throttle behavior already available via the drag pad.

### Final change
- Removed Speed slider UI from `ui_manual_panel.py`.
- Removed all slider logic from `ui_script.py`.
- Manual control uses the drag pad only (X=steering, Y=throttle).

### Verification
- Confirm no slider is visible.
- Drag pad still controls steering/throttle.
- Stop button still returns to neutral.

---

## 4) Download zipped recording (dropdown + download button)
### What’s new
- Record panel now includes:
  - **Toggle Rec**
  - **Download ZIP**
  - **Dropdown** listing available sessions

### Backend
- Added routes:
  - `GET /api/record/list` → returns `{ sessions: [...] }`
  - `GET /api/record/download?session=YYYYMMDD-HHMMSS` → returns a zip
- ZIP is generated into a **temporary file** (safer for large sessions) and deleted after response.
- Session name is validated with regex to prevent path traversal.

### Frontend
- On page load: fetches `/api/record/list` to populate dropdown.
- When recording transitions **ON → OFF**, it refreshes the dropdown so the newest session appears.
- Download uses `window.location = ...` so the browser handles the file download normally.

### Verification
1) Toggle Rec ON, drive a bit, Toggle Rec OFF.
2) Open dropdown → newest timestamped folder should appear.
3) Select session → click **Download ZIP**.
4) Confirm the ZIP contains:
   - `<session>/records.jsonl`
   - `<session>/images/*.jpg`

---

## Files changed
- `ui_base.py`
- `ui_manual_panel.py`
- `ui_record_panel.py`
- `ui_status_panel.py`
- `ui_script.py`
- `video_stream.py`
- `control_api.py`
- `server.py`

---

## Future improvements
- Add a **“Refresh”** icon next to the dropdown (manual refresh).
- Add a **“Delete recording”** option with confirmation.
- Show recording size / frame count in the dropdown.
