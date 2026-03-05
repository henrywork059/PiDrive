# PiCar Patch Notes — piCar_0_3_2

Date: 2026-03-05

## Summary
This patch expands the per-frame `records.jsonl` schema so each recording line now also stores:

- `frame_id`
- `session`
- `mode` (already present, kept)
- Camera metadata: `cam_w`, `cam_h`, `format`

It keeps backward compatibility by retaining existing fields (`frame`, `ts`, `image`, `image_id`, `steering`, `throttle`, `mode`).

## Problem / Cause
You requested additional metadata to be stored per recorded frame so:
- frames can be traced back to the session reliably,
- tooling (PC-side trainer / dataset tools) can understand capture configuration,
- schema is explicit and consistent across devices.

The existing recorder only stored control labels + image path + timestamp, but not the camera config or session id.

## Attempted Fixes
- Considered storing metadata only once in a separate session-level file.
- Decided instead to store the requested fields per frame to keep each JSONL line self-contained (simplifies downstream tooling and partial dataset merges).

## Final Changes
### 1) `data_recorder.py`
- Added the requested fields to each JSONL record:
  - `frame_id` (alias of `frame`)
  - `session` (session folder name)
  - `cam_w`, `cam_h` (camera configured size)
  - `format` (camera pixel format string)
- Also added two optional convenience fields:
  - `img_w`, `img_h` (actual stored image dimensions)
  - `image_format` ("jpg")

### 2) `camera.py`
- Added `self.format = "BGR888"` so the recorder can reliably read `camera.format`.
- Camera configuration now uses `self.format` (no behavior change).

## Compatibility Notes
- Existing consumers that read `frame` will continue to work.
- New consumers can prefer `frame_id` and `session`.

## Verification Steps
On the Raspberry Pi:
1. Start server:
   - `python3 server.py`
2. Start a recording session (toggle REC), drive for a few seconds, stop.
3. Open the latest session file:
   - `data/records/<session>/records.jsonl`
4. Confirm each JSON line includes:
   - `frame_id`, `session`, `mode`, `cam_w`, `cam_h`, `format`
5. Confirm images are still written and readable.

## Future Improvements
- Add a session-level `meta.json` (camera config, device info, model name, commit hash) to avoid repeating constant data on every line.
- Optionally record full-resolution frames (426x240) rather than preview-resized frames, if training quality needs it.
