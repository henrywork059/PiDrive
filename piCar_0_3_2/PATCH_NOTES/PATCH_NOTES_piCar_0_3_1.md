# PiCar Patch Notes — piCar_0_3_1

Date: 2026-03-05

This patch focuses on **recording management + data hygiene**, and also normalizes the project layout so **all patch notes live inside `PATCH_NOTES/`**.

---

## 1) All patch notes moved into `PATCH_NOTES/`

### Problem
Some older patch note files were stored in the project root (e.g., `PATCH_NOTES_piCar_0_1_0.md`), while newer ones were stored in `PATCH_NOTES/`. This made the repo messy and inconsistent.

### Fix
- Moved **all** `PATCH_NOTES_*.md` files into:
  - `PATCH_NOTES/`

### Result
- Project root stays clean.
- Patch note history is consistently organized in one folder.

---

## 2) Add “Delete selected recording” button (UI + API)

### Problem
You can now download a selected recording ZIP, but there was no way to delete old sessions from the web UI, which will quickly fill up the SD card.

### Fix
**Frontend**
- Added a new **Delete** button next to the **Download ZIP** button in the Recording panel.
- Added confirmation prompt to prevent accidental deletions.

**Backend**
- Added new API endpoint:
  - `POST /api/record/delete` with JSON body `{ "session": "YYYYMMDD-HHMMSS" }`
- Safety guard:
  - Refuses to delete the **currently active** session if recording is running.

### Result
- You can delete recordings safely without SSH.
- SD card storage is easier to manage.

---

## 3) Timestamp-based image IDs (unique + sortable)

### Problem
Images were named sequentially (`000001.jpg`, `000002.jpg` ...). While that is fine *inside* a session folder, it becomes annoying when:
- You extract multiple sessions into one place
- You want the images to be sortable by capture time across sessions
- You want to guarantee no filename collisions

### Fix
- Changed recorded image filename format to include capture time + frame counter:

  `YYYYMMDD-HHMMSS-ffffff_000001.jpg`

- Added an `image_id` field into `records.jsonl` (keeps backward compatibility, since existing fields remain):

  ```json
  {
    "frame": 1,
    "ts": 1700000000.123,
    "image": "images/20260305-101530-123456_000001.jpg",
    "image_id": "20260305-101530-123456_000001",
    "steering": 0.12,
    "throttle": 0.45,
    "mode": "manual"
  }
  ```

### Result
- Recorded images sort naturally by time.
- If you merge sessions later, filenames won’t collide.
- Training tooling remains compatible because `image` path still exists.

---

## Files Changed
- `data_recorder.py`
  - Timestamp-based image filenames + `image_id` field
- `ui_record_panel.py`
  - Added Delete button
- `ui_script.py`
  - Added `deleteSelectedRecording()` function
- `control_api.py`
  - Added session delete helper with safety guard
- `server.py`
  - Added `POST /api/record/delete`
- Project layout
  - Moved all `PATCH_NOTES_*.md` into `PATCH_NOTES/`

---

## Verification Checklist
On the Pi:
1. Start the server:
   ```bash
   cd ~/piCar
   python3 server.py
   ```
2. Open the Web UI on phone/PC.
3. Recording:
   - Toggle Rec ON, drive for a few seconds, Toggle Rec OFF.
   - Confirm a new session appears in dropdown.
4. Download:
   - Select the session → Download ZIP → confirm `<session>.zip` downloads.
5. Delete:
   - Select the session → Delete → confirm it disappears from the dropdown.
6. Filename format:
   - Unzip the downloaded recording and confirm images are named like:
     - `YYYYMMDD-HHMMSS-ffffff_000001.jpg`

---

## Notes / Future Improvements
- Add a storage indicator (free space) in the Recording panel.
- Add "Delete all recordings" with a double-confirm safety.
- Optional: add a "preview first/last frame" thumbnail for the selected session.
