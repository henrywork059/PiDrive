# PiSD 0.10.9 Patch Notes

## Request summary

- Keep preview action buttons above the camera/preview image in every PiSD mode/page.
- Improve recording frame ID naming so IDs do not repeat when two recording sets from different days/sessions are merged for training.

## Baseline and anti-rollback source

This patch was built forward from:

1. `PiSD_0_10_0.zip`
2. accepted patches `PiSD_0_10_1_patch.zip` through `PiSD_0_10_8_patch.zip`

The patch was checked against the previous accepted AI/Manual Drive work so it does not roll back:

- one-button `Start live` workflow
- Manual Drive `r` recording and `s` snapshot shortcuts
- AI Mode `r` recording and `s` snapshot shortcuts
- AI Mode `Limiter / correction / manual` three-pane panel
- additive correction equation: `AI + manual * Correction %`
- fixed-throttle-after-correction behaviour
- full Manual pad takeover
- AI recording download panel
- global Space STOP
- AI max-throttle persistence from `0_10_8`
- split AI correction/safety helper modules from `0_10_5`

## Cause / root cause

### Preview buttons

Some preview action controls were placed below large preview images. On a small screen or when the preview grows, the user may need to scroll past the image before seeing important actions such as `Start live`, `Snapshot`, `Record`, or AI run controls.

### Frame ID naming

The recording metadata already stored session and timestamp information, but trainer-facing workflows can still become confusing if they treat simple per-session frame names/order numbers as identifiers. When two days or sessions are merged, loose identifiers such as `frame_000001` are not globally unique.

## Files changed

### Runtime / recording

- `pisd/services/recording_service.py`
  - Added `_make_frame_identity()` helper.
  - New frame IDs use a globally unique session/date/UUID-based format.
  - JPEG filenames now use the same globally unique frame ID.
  - `records.jsonl` entries include:
    - `frame_id`
    - `frame_id_scheme`
    - `frame_id_unique_scope`
  - `labels.jsonl` entries now also include:
    - `frame_id`
    - `frame_index`
    - `frame_id_scheme`
  - Manifest training label schema now documents `frame_id`.

### Preview button placement

- `pisd/web/templates/manual_drive.html`
  - Moved `Start live`, `Snapshot`, and `Record` above the Manual Drive preview frame.

- `pisd/web/templates/ai_mode.html`
  - Moved `Start AI preview`, `Start AI drive`, and `Stop AI` above the AI preview frame.
  - Existing `Start live`, `Snapshot`, and `Record` camera buttons remain above the AI preview frame.

- `pisd/web/templates/main_dashboard.html`
  - Moved `Start camera + live` and `Stop camera only` above the dashboard preview frame.

- `pisd/web/templates/testing_server.html`
  - Moved testing camera/action buttons above the testing preview image.

### Styling

- `pisd/web/static/css/manual_drive.css`
  - Added top-of-preview action row spacing.

- `pisd/web/static/css/ai_mode.css`
  - Updated AI run-action spacing for the new above-preview position.

- `pisd/web/static/css/main_dashboard.css`
  - Added dashboard top-of-preview action styling.

- `pisd/web/static/css/pisd_layout_system.css`
  - Added testing page layout override so the testing action row stays above the preview even when global layout overrides are active.

### Tests / validation

- `scripts/test_manual_drive_page.py`
  - Added static contract check that Manual Drive preview buttons appear before the preview frame.

- `scripts/test_ai_mode_page.py`
  - Added static contract check that AI camera/run buttons appear before the preview frame.

- `scripts/test_main_dashboard.py`
  - Added static contract check that dashboard preview buttons appear before the preview frame.

- `scripts/test_testing_server_gui.py`
  - Added static contract check that testing preview buttons appear before the preview image.

- `scripts/test_recording_service.py`
  - Added checks for globally unique `frame_id` values in single captures.
  - Added checks for `frame_id_scheme` and trainer label `frame_id` fields.

### Version / docs

- `pisd/__init__.py`
  - Version updated to `0.10.9`.

- `README.md`
  - Updated current patch line to `PiSD_0_10_9`.
  - Documented top-of-preview buttons and global frame ID naming.

- `docs/RECORDING_DATA.md`
  - Updated frame/folder examples to show the new globally unique frame filename/ID style.
  - Documented `frame_id` in trainer labels.

- `docs/TEST_PLAN.md`
  - Added `0.10.9` verification steps.

- `docs/STABLE_BASELINE.md`
  - Added `0.10.9` forward-patch notes while keeping `0_10_0` as the rollback baseline.

- `docs/AI_MODE_CODE_MAP.md`
  - Added note that AI camera and run controls now stay above `#aiPreviewFrame`.

## Exact behavior changed

### Preview controls

Preview controls are now consistently located before the preview frame/image:

- Manual Drive: `Start live`, `Snapshot`, `Record`
- AI Mode: `Start live`, `Snapshot`, `Record`, `Start AI preview`, `Start AI drive`, `Stop AI`
- Dashboard: `Start camera + live`, `Stop camera only`
- Testing Server: camera start/stop/snapshot/config/capability diagnostic buttons

### Recording IDs

New saved frame IDs follow this shape:

```text
pisd_<session-or-date-id>_f000001_<utc-stamp>_<uuid>.jpg
```

Example:

```text
pisd_20260608_145500_manual_drive_a1b2c3d4_f000001_20260608t065501123456z_ab12cd34ef.jpg
```

The same value is stored as `frame_id` in both `records.jsonl` and `labels.jsonl`.

Existing trainer-facing path fields remain in place:

- `frame`
- `relative_file`
- `steering`
- `throttle`
- `timestamp_utc`
- `session_id`

## Verification actually performed

The patch was applied over a clean extracted `PiSD_0_10_0.zip` plus accepted patches `0_10_1` through `0_10_8`, then these checks were run:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/main_dashboard.js
node --check pisd/web/static/js/testing_server.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_testing_server_gui.py --static-only
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All checks above passed.

A fuller validation command without `--skip-api` was also attempted:

```bash
python3 scripts/run_standard_validation.py --skip-camera --skip-motor --skip-gui
```

That failed only because Flask is not installed in this packaging container:

```text
PISD-APP-002: Flask is not installed. Run: python -m pip install -r requirements.txt
```

## Known limits / next steps

Not hardware-verified in this container:

- real Pi browser layout with the preview controls above the frame
- real camera stream in Manual Drive, AI Mode, Dashboard, and Testing Server
- real recording sessions across two different dates
- real piTrainer import/merge of multiple sessions using the new `frame_id`
- real motor output and Space STOP response
- real AI model inference
