# PiSD Recording and Frame Data

PiSD saves manual-drive screenshots and recording sessions under `PiSD/recordings/`.

## Folder structure

One-off captures:

```text
recordings/
  single_captures/
    YYYY-MM-DD/
      frames/
        frame_000001_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg
      manifest.json
      records.jsonl
      labels.jsonl
```

Recording sessions:

```text
recordings/
  YYYY-MM-DD/
    YYYYMMDD_HHMMSS_manual_drive_xxxxxxxx/
      frames/
        frame_000001_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg
        frame_000002_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg
      manifest.json
      records.jsonl
      labels.jsonl
```

## Traceability

Every saved frame has the original PiSD `frame_id` format and a 1-based `frame_index`. The saved image filename uses the shorter `frame_000001_<utc-stamp>_<uuid>.jpg` style, while the full `records.jsonl` entry keeps the session id, timestamp, and motor/camera state for traceability.
The JSONL record beside the image stores:

- `saved_at_utc`, `date`, and `time`
- camera frame sequence and source timestamp
- `frame_id` and relative image file path
- full camera settings/status
- full motor settings/status
- steering, throttle, steer mix
- effective left/right motor outputs
- motor tuning values such as bias, directions, and max speed
- Manual Drive visual path overlay settings used when the frame was saved

This means a training or debugging script can link every frame back to the exact runtime state that produced it. From PiSD 0.6.7 onward, piTrainer can also redraw the path overlay from the saved overlay metadata instead of guessing the current browser settings.

## API endpoints

```text
GET  /api/recording/status
POST /api/recording/capture
POST /api/recording/start
POST /api/recording/stop
```

Example capture:

```bash
curl -X POST http://127.0.0.1:5050/api/recording/capture \
  -H "Content-Type: application/json" \
  -d '{"label":"manual_capture"}'
```

Example recording session:

```bash
curl -X POST http://127.0.0.1:5050/api/recording/start \
  -H "Content-Type: application/json" \
  -d '{"label":"manual_drive","fps":6}'

curl -X POST http://127.0.0.1:5050/api/recording/stop
```

## Development rules

- Do not save frames directly from GUI code.
- Use `RecordingService` and `/api/recording/*` so metadata stays consistent.
- Do not write to `config/defaults.json` for user runtime data.
- Do not include generated `recordings/` or `test_outputs/` folders in patch zips.


## Folder policy updated in PiSD 0.3.6

Continuous recording sessions each use their own folder:

```text
PiSD/recordings/YYYY-MM-DD/YYYYMMDD_HHMMSS_<label>_<id>/
  frames/
  manifest.json
  records.jsonl
```

Manual single captures are different. They are all saved into the same folder for the current day:

```text
PiSD/recordings/single_captures/YYYY-MM-DD/
  frames/
  manifest.json
  records.jsonl
```

This avoids creating one tiny folder for every quick screenshot while still keeping each frame traceable by `frame_id`, `frame_index`, date, time, source camera frame sequence, camera settings, motor settings, steering/throttle command, and motor output values.

The Manual Drive page displays a visible confirmation message after a frame is captured. When recording is active, it also shows a red recording indicator in the camera panel.

## 0.3.8 recording library management

PiSD now exposes the saved recording/snapshot folders to the browser GUI.

### Folder list

```text
GET /api/recording/items
```

Returns two folder lists:

- `recordings` — one folder per continuous recording session
- `snapshots` — daily single-capture folders under `recordings/single_captures/YYYY-MM-DD/`

### Download selected folder as zip

```text
GET /api/recording/download.zip?kind=recording&id=YYYY-MM-DD/session_id
GET /api/recording/download.zip?kind=snapshot&id=single_captures/YYYY-MM-DD
```

The selected folder is zipped with a top-level folder prefix so the files remain traceable when downloaded to a PC.

### Delete selected folder

```text
POST /api/recording/delete
Content-Type: application/json

{"kind":"recording","id":"YYYY-MM-DD/session_id"}
{"kind":"snapshot","id":"single_captures/YYYY-MM-DD"}
```

Deleting the active recording session is refused. Stop recording first.

### Safety rules

- Folder IDs are relative to `PiSD/recordings/`.
- Parent traversal such as `../` is rejected.
- Missing folders return `PISD-REC-008`.
- Delete failures return `PISD-REC-009`.
- Zip failures return `PISD-REC-010`.


## 0.6.7 overlay metadata for trainer redraw

Manual screenshots and continuous recordings now save the active Manual Drive path-overlay settings alongside each frame. This is separate from the camera image itself; it is metadata for later visualisation in piTrainer.

Saved locations:

- `manifest.json` stores the latest/session-level `overlay_settings`, `overlay_settings_source`, and `overlay_schema_version`.
- `records.jsonl` stores `overlay_settings` on every full frame record.
- `labels.jsonl` also stores `overlay_settings` beside the compact trainer fields.

Example `labels.jsonl` row shape:

```json
{
  "frame": "frames/frame_000001_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg",
  "relative_file": "recordings/YYYY-MM-DD/session/frames/frame_000001_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg",
  "steering": 0.12,
  "throttle": 0.18,
  "timestamp_utc": "2026-05-18T14:30:00.000000+00:00",
  "source_frame_seq": 1,
  "session_id": "YYYYMMDD_HHMMSS_manual_drive_xxxxxxxx",
  "overlay_schema_version": "PiSD_0_6_7_overlay_settings_v1",
  "overlay_settings": {
    "enabled": true,
    "path_length_scale": 1.0,
    "curve_strength": 3.35,
    "opacity": 0.94,
    "path_width_scale": 0.34
  }
}
```

The overlay settings are visual-only metadata. They do not change motor outputs. User-entered unclamped overlay tuning numbers are preserved where they are finite JSON-safe values, so piTrainer can reproduce the same guide style used during recording.
