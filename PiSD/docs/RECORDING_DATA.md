# PiSD Recording and Frame Data

PiSD saves manual-drive screenshots and recording sessions under `PiSD/recordings/`.

## Folder structure

One-off captures:

```text
recordings/
  snapshots/
    YYYY-MM-DD/
      snapshot_YYYYMMDDTHHMMSSffffffZ_label_xxxxxxxx/
        frames/
          frame_000001_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg
        manifest.json
        records.jsonl
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
```

## Traceability

Every saved frame has a unique `frame_id` and a 1-based `frame_index`.
The JSONL record beside the image stores:

- `saved_at_utc`, `date`, and `time`
- camera frame sequence and source timestamp
- relative image file path
- full camera settings/status
- full motor settings/status
- steering, throttle, steer mix
- effective left/right motor outputs
- motor tuning values such as bias, directions, and max speed

This means a training or debugging script can link every frame back to the exact runtime state that produced it.

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
