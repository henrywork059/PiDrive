# PiSD

## R48 read-only startup preflight (0.11.21)

The PiSD **front page** now has a collapsed **Startup preflight** with
**Refresh checks**. Its only request is `GET /api/preflight`. The server
reads the existing camera/motor/AI status snapshots and passive
`shutil.disk_usage`; no camera start, motor update/stop, model load,
settings reset, subprocess or new network probe occurs.

Six concise rows show requested vs actual service mode (simulation and
hardware **must not** be conflated), whether the Picamera2 camera is
actually running, whether an AI model is ready and TFLite runtime imports
appear available, actual GPIO adapter vs simulation/fallback and the
camera-fault safety latch, available recording disk space, and HTTP reachability
**to this PiSD process only**. Internet/router/Wi-Fi connectivity is not
claimed, and unknown disk data contains no exception/absolute path.

To run targeted tests from repository root:
```bash
cd PiSD
python -m unittest discover -s scripts -p 'test_preflight_r48.py' -v
cd ..
node --test PiSD/scripts/test_preflight_ui_r48.cjs
```
Release requires real Pi hardware/simulation checks, TFLite installed/missing,
camera off/on, missing model and low disk, plus R35 STOP, R43 hidden-tab
MJPEG and complete PiSD regression suites. The existing PiSD.py launcher
and `pisd.service` hardware selection are not modified.

## R47 failed-request trace IDs and safe PiSD error history (0.11.20)

Each unsuccessful `/api/*` mutation (including `HTTP 200` with
`ok:false`) keeps the previous error/status-code contract and gains a
server-issued `correlation_id`, `operation` and `X-Correlation-ID`
response header. A matching bounded log line is emitted as
`api_mutation_failure id=<ID> operation=<name> http_status=<status>`.
Neither the request body nor operator secrets/paths are logged by this
hook. Lookup is via the PiSD process log (e.g. `journalctl -u pisd` if
that service name is configured). IDs are not accepted from clients.

Manual Drive and AI Mode expose **Error details** next to existing
status/log text, limited to the reference, operation, HTTP status and
existing PiSD error code. Rejected camera Start, STOP, driving or recording
commands are not incorrectly reported as confirmed. Existing latched
safety, hardware-control and R43 hidden MJPEG handling are untouched.
`ErrorReport.as_dict()` now scrubs credential/absolute path values from
`/api/errors`, error status histories and embedded `error` diagnostics;
traceback text is never exported, even in explicitly requested history
views. No new persistent error stores or cloud exports.

Tests (repo root):
```bash
python -m unittest discover -s PiSD/scripts -p 'test_request_trace_r47.py' -v
node --test PiSD/scripts/test_request_trace_ui_r47.cjs
```
Review actual Pi response status and physical safety behavior on device:
invalid settings, rejected camera Start, motor STOP fail and AI preview/drive
safety, HTTP 200/400/500 errors, and error-history redaction.

## Hidden-tab MJPEG bandwidth (0.11.18, R43)

Manual Drive and AI Mode close their browser `/video_feed` MJPEG connection
when the tab becomes hidden, and restore it on visibility **only if live
preview was still selected**. The legacy bench dashboard follows the same
behavior. The server-side camera, recording and motor services are **not**
stopped by this display-only change. The existing Manual Drive fail-safe
STOP on hide and AI correction/manual/assist/AI stop handlers run before
the stream is paused. The existing per-page preview-FPS polls and readiness
checks remain guarded. AI Mode's 250 ms **read-only UI status timer** skips
hidden tabs and coalesces in-flight reads; it does not change the actual
AI model inference or motor-control loop frequency.

PiSD already supplies server `timestamp_utc` status freshness and measured
frame sequence/age via `/api/camera/fps-stats`; R43 does not replace these
with client wall-clock guesses.

**Expected bandwidth profile:** a visible live MJPEG connection keeps a
single long-lived HTTP response continuously streaming JPEG frames; a
hidden tab now closes that response, targeting **zero hidden-tab MJPEG
payload bytes**. There is no meaningful requests-per-minute value for a
single long-lived stream. Actual bytes/sec saved depend on the camera
codec, frame size/rate and browser connection lifetime and are **not
measured** in this environment.

Run `node --test PiSD/scripts/test_adaptive_stream_r43.cjs` from the
monorepo root. Before release, capture HTTP/network bytes for active,
hidden and visible-again scenarios and verify immediate fresh server frame
sequence/age, motor STOP/Space STOP, AI stop, recording continuity and
the latest R35/R36 responsive layouts on actual Raspberry Pi hardware.

## Model compatibility and rollback (0.11.12, U27)

PiSD understands optional `<model>.tflite.manifest.json` and
`<model>.keras.manifest.json` sidecars. New piTrainer exports contain
the steering model family, RGB/NHWC geometry, input normalization, ordered
steering/throttle output semantics, quantization mode, training seed and
SHA-256 checksum. A present manifest with the wrong family, altered bytes
or mismatched shape is **rejected before activation**. A sidecar-free legacy
model remains loadable with a visible warning and tensor inspection.

PiSD now tests a replacement model with a synthetic input before changing
the working interpreter or saved model ID. Unsupported YOLO detectors, wrong
shapes, non-finite outputs and invalid quantization are refused. If
preflight fails, the previous active model stays selected. Stop AI preview
or driving before attempting a model swap.

The upload API accepts an optional multipart `manifest` file alongside
`model`. The manifest is verified against the uploaded model bytes; a
failure leaves the existing model selection untouched. Deleting a model
also removes its matching sidecar. For offline deployments, copy the
model and sidecar together into `PiSD/models/`. Old models remain
supported; the extra file is not mandatory.

Real Raspberry Pi model loading, TensorFlow Lite implementation differences,
safety-stop timing, and browser upload workflows require on-device tests.
This update does not bypass the accepted AI camera-staleness latch, motor
safety, storage limits or recording recovery.

`PiSD_0_11_12` model-deployment safety update — layered on the current PiSD 0.11.10 diagnostic branch while retaining accepted 0.11.x UI/settings changes.

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behaviour patterns, but PiServer files must not be overwritten by PiSD experiments.

Future bug-fix patches after this package should use `PiSD_0_11_x_patch` naming unless a newer stable line is promoted.

## Current version

`PiSD_0_11_12` forward patch. The uploaded `PiSD_0_11_0.zip` is a historical full baseline; the active GitHub branch includes the accepted 0.11.7–0.11.10 changes. This patch keeps the AI preview/manual-recording separation, then adds the AI workflow settings popup, camera FPS control, manual-release preview preservation, and moves the motor confirmation into the AI workflow panel.

Use the latest accepted GitHub patch branch as the source-of-truth for forward changes; do not revert to the historical 0.11.0 ZIP.

Included accepted work:

- Manual Drive overlay toggle on the Manual Drive page.
- Road-guide overlay presentation using a filled drivable path corridor plus two thin left/right road-edge guide lines.
- Straight overlay forms a perspective trapezium; turning overlay uses sampled kinematic-style path geometry.
- Road edges are offset using local tangent normals, so inner and outer sides bend more naturally.
- Shared overlay geometry helper used by both Manual Drive and AI Mode.
- Corrected overlay left/right turn direction in the shared helper.
- Reverse-motion overlay drawing hidden; reverse steering policy remains same-sign.
- Overlay settings now use numeric inputs in a popup instead of sliders/drop-down controls.
- Overlay values are no longer clamped back to old slider ranges when typed or saved.
- Manual Drive overlay tuning is reduced to seven visual-only controls, and the values are accepted without old UI min/max caps.
- Screenshots and continuous recordings include `overlay_settings.json` and `overlay_settings_history.jsonl` for future piTrainer redraw.
- Clear one-button live-preview workflow: Manual Drive and AI Mode show the short `Start live` label, while Dashboard/Testing keep the technical combined camera/live wording for diagnostics.
- Status-only refresh that does not start the camera or send motor commands.
- Page-leave motor fail-safe stop.
- Manual Drive now supports keyboard driving: ↑/↓ adjust live throttle by `0.05` per press, holding ←/→ ramps steering by full scale in `0.8 s`, Space stops, `r` toggles recording, and `s` saves a snapshot.
- Preview idle start, FPS estimate, frame-age display, stale-frame warning, and guarded preview metrics loop.
- Recording/snapshot selected-folder details, safer download/delete button states, and hardened backend folder-id validation.
- Manual Drive recordings include trainer-friendly `labels.jsonl` beside full `records.jsonl` metadata.
- Recording frame names/IDs are restored to the original PiSD format after the experimental `0_10_9` global-id scheme was found too complicated for the current workflow.
- AI Mode page at `/ai-mode`, replacing the earlier scripted Autopilot foundation.
- Legacy `/autopilot` path is retained only as a retired compatibility/redirect path to AI Mode.
- AI Mode model listing/loading from `PiSD/models/` and a guarded safety layer between AI predictions and motor output.
- AI Mode can save snapshots, start/stop recording, and download/delete saved recording or snapshot folders through the shared recording service, using the same recording folder format as Manual Drive.
- AI Mode max throttle and fixed throttle controls allow full-scale `1.00`; AI prediction FPS can be set up to `60` when the Pi/model can keep up.
- AI Mode preview reuses the Manual Drive preview-frame design, keeps Start live/Snapshot/Record and Start AI preview/Start AI drive/Stop AI above the camera view, and draws the road-guide overlay from the model prediction after the safety limiter.
- AI Mode `Limiter / correction / manual / assist` panel has four panes: Limiter settings, additive AI Correction, full Manual pad takeover, and AI steering assist.
- AI Mode supports `r` to toggle recording and `s` to save a snapshot when focus is not inside a text field or popup editor. Space is now a global STOP shortcut across PiSD pages and AI panels.
- AI correction percentage is user-settable; fixed-throttle mode still enforces the configured fixed throttle after steering correction. The full Manual pad uses the same guarded `/api/control/manual` path as Manual Drive and directly takes over from AI drive control. The correction equation now lives in `pisd/services/ai_correction.py`, while fixed-throttle/limiter math lives in `pisd/services/ai_safety.py` for smaller, easier-to-debug backend scripts.
- AI steering-only mode keeps fixed throttle while driving straight.
- AI motor-output enable is live/session-only and is not persisted across reloads.
- Manual Drive backend now enforces the saved max speed limit in `/api/control/manual`.
- Hardware Manual Drive API commands require live safety and motor-output acknowledgement.
- Manual Drive no longer overrides saved motor `steer_mix`; motor mixing is controlled by the motor settings.
- Default motor steering mode is now `turn_rate`: left/right input controls curve tightness while up/down controls travel speed along that curve. The older `arcade_mix` behaviour remains selectable as a fallback.
- The Manual Drive and AI Mode overlays are visual-only calibration layers. They are manually tuned to match the real camera view and real car motion instead of being driven by motor tuning values.
- Motor Tuning at `/motor-tuning` has been cleared in patch `0_8_7` so the calibration workflow can be rebuilt from a clean page. The backend motor service, linear X steering, and overlay settings remain available for the next design.
- Dashboard is labelled as a legacy/development comparison shell, with stale speed limits raised to full-scale to avoid conflicting with current Manual Drive limits.
- Default OV5647 camera profile code includes the attempted `03_request_awb_off_lock` request/PIL RGB visual profile and safe runtime migration. This still needs real Pi confirmation if colour does not match the earlier 03/91 diagnostic captures on a specific camera.

This stable baseline keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` must not be restored.

## Motor tuning workflow

Patch `0_8_7` intentionally clears the `/motor-tuning` page. The previous safety, timed motion, live preview, overlay controls, motor settings, and log panels were removed so the page can be rebuilt cleanly.

The backend pieces remain available for the next design:

- `/api/motor/tune-run` still runs a timed command through the normal motor steering algorithm and stops in a `finally` path.
- Linear X steering remains active in `MotorService`: `x = 0.5` gives a half-tight turn and `x = 1.0` gives the tightest non-pivot turn.
- Overlay calibration remains visual-only and separate from motor output.

Until the new tuning page is rebuilt, use Manual Drive and backend/API checks for live car testing.

## Manual Drive keyboard control

Manual Drive supports keyboard control after motor output is enabled and the browser focus is not inside an input field:

```text
Arrow Up    throttle +0.05 per press
Arrow Down  throttle -0.05 per press
Hold Left   steering ramps toward -1.00 at full scale in 0.8 s
Hold Right  steering ramps toward +1.00 at full scale in 0.8 s
Space       STOP motors and clear keyboard throttle/steering
```

Keyboard commands use the same `/api/control/manual` path as the drag pad, so they keep the same safety acknowledgement, intended-output display, recording labels, and linear X steering behaviour.

## AI Mode workflow

PiSD AI Mode follows a DonkeyCar-style behavioural-cloning workflow while keeping PiSD's own lightweight web UI and motor service:

```text
Manual Drive recording
  camera frame + steering + throttle + overlay settings
        ↓
recordings/.../frames + records.jsonl + labels.jsonl
        ↓
train/export model on PC or trainer tool
        ↓
upload/copy model into PiSD/models/
        ↓
AI Mode loads model → predicts steering/throttle → safety limiter → motor service
```

Supported model file discovery currently includes:

```text
.tflite, .keras, .h5, .onnx, .pt
```

Runtime inference is implemented for piTrainer-exported `.tflite` models when a TFLite runtime backend is installed, and for piTrainer-exported `.keras`/`.h5` models when TensorFlow is installed. PiSD reads piTrainer's named `steering` and `throttle` outputs, including Keras dict/list outputs and TFLite one-tensor or two-tensor outputs. `.onnx` and `.pt` files are listed so the UI can see them, but they are not runnable until a future backend is added.

The TFLite loader tries these Python backends in order:

```text
tflite_runtime.interpreter
ai_edge_litert.interpreter
tensorflow.lite.Interpreter
```

The **Limiter / correction / manual** panel has three panes. **Limiter** keeps the existing output safety settings. **Correction** lets the user correct the AI with the same control style as Manual Drive: drag the pad, use arrow keys, press `r` to toggle recording, and press `s` to save a snapshot. **Manual pad** is a direct takeover pad. Space is reserved for global STOP instead of centring correction. The **Correction %** slider controls how strongly the manual correction is added to the model prediction:

```text
corrected steering = AI steering + manual steering correction * correction_percent
corrected throttle = AI throttle + manual throttle correction * correction_percent
```

The corrected command is clamped and then passed through the existing AI safety limiter and motor-output checks. If `AI steering + fixed throttle` is selected, the final throttle still comes from the fixed-throttle value after the steering correction is applied.

The **Model file** panel can upload a model from the browser to `PiSD/models/` and can delete a selected model from the Pi. Upload uses a safe filename and appends a timestamp if the same filename already exists. The panel also shows runtime diagnostics. If `Backend` shows `load_failed` or `Runtime` shows `TFLite missing`, install a compatible TFLite backend in the same Python environment that runs PiSD, restart PiSD, and click **Load model** again. PiSD includes helper commands for this:

```bash
cd ~/PiDrive/PiSD
python3 scripts/install_ai_runtime.py --runtime tflite-runtime
python3 scripts/check_ai_runtime.py
```

If `tflite-runtime` is unavailable on that Pi/Python combination, try:

```bash
python3 scripts/install_ai_runtime.py --runtime ai-edge-litert
python3 scripts/check_ai_runtime.py
```

See `docs/AI_RUNTIME_SETUP.md` for the full runtime setup note.

AI reverse steering policy remains **same sign**: when throttle is negative, PiSD does not flip the steering value. The current road-guide overlay does not draw reverse motion.

AI drive is blocked unless:

- a runnable model is loaded;
- the safety acknowledgement is checked;
- motor output is enabled for the current live session;
- the AI safety limiter clamps the prediction to saved max steering/throttle limits.

Focused validation:

```bash
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_ai_drive_service.py
```

## Recording data structure

Continuous Manual Drive recording sessions are stored under:

```text
PiSD/recordings/YYYY-MM-DD/YYYYMMDD_HHMMSS_manual_drive_xxxxxxxx/
  frames/
  manifest.json
  records.jsonl
  labels.jsonl
```

Single captures are stored under:

```text
PiSD/recordings/single_captures/YYYY-MM-DD/
  frames/
  manifest.json
  records.jsonl
  labels.jsonl
```

For piTrainer, use `labels.jsonl` first:

```text
image → steering, throttle, overlay_settings
```

Use `records.jsonl` only for full debug metadata, filtering, or advanced training options. If a frame-level overlay value is missing, fall back to `records.jsonl`, then `manifest.json`, then trainer defaults.

## PiSD 0.11.11 — Recording disk-space protection (U26)

PiSD now checks recording filesystem capacity before starting a session, before
saving single captures and before writing each recording JPEG/JSONL pair.
The defaults are **512 MiB warning** and **256 MiB critical reserve**, plus
the estimated next JPEG/metadata write. Configure them through the service
environment without resetting persistent PiSD settings:

```bash
export PISD_RECORDING_WARN_FREE_MB=512
export PISD_RECORDING_MIN_FREE_MB=256
```

The existing `GET /api/recording/status` (and general status) includes a
`recording.storage` object with `state` (ok/warning/critical/unavailable),
`free_bytes`, `total_bytes`, `session_size_bytes` and the last five write
errors. The session-size scan is cached for two seconds to avoid repeated SD
card directory walks. A warning does not stop recording; **critical or
unavailable space refuses new writes**. If an existing recording's write fails,
the recording thread stops and attempts to finalise its manifest; a failed
finalisation remains recoverable with the 0.11.9 offline recovery utility.

**Motor driving, camera preview, and AI output are not stopped by a
recording-only storage failure.** For actual motion safety, existing e-stop
and watchdog behavior still applies. A stopped recording does not automatically
resume after space is freed; start it explicitly.

**No automatic cleanup.** Download or back up recordings first. The existing
file-library GUI asks for confirmation and the delete API now requires
`{"kind":"recording","id":"...","confirm":true}` (or a selected
snapshot folder). Only the selected non-active folder can be deleted.
Never manually remove an active recording folder.

A disk-full failure during a multi-file save may leave an orphan JPEG or
unmatched JSONL row. The existing U20 offline recovery tool remains the
correct way to inspect and reconcile that session; this is not a database
transaction. Check the storage status on a Raspberry Pi before tuning the
reserve for an SD card.

## PiSD 0.11.10 — Runtime latency diagnostics (U23)

Camera and AI status include a `performance` object with bounded rolling p50/p95
latencies. Camera measures capture-loop work and JPEG encode; AI measures JPEG
decode, resize/array preparation, inference (new frames only), safety/postprocess,
motor apply, and controller-loop work. Existing camera FPS, frame age, encode
averages and stale-frame safety indicators remain unchanged. Diagnostics also
include dropped/stale frames, reused predictions, and inference failures.

Use the existing authenticated status endpoints:
`/api/status`, `/api/ai/status`, and camera status/FPS APIs. Process CPU
percent is sampled on status reads at intervals of at least one second; it
can exceed 100% with multiple CPU cores. Empty/unmeasured stages are omitted,
**not** reported as zero latency. Queue-wait latency is not included because
these runtime paths do not expose a discrete timestamped work queue.

The rolling window holds at most 120 observations per stage, no performance
samples are written to SD card, and verbose per-frame logging is off. These
measurements are diagnostic observations, not calibrated end-to-end actuation
latencies or a guarantee of motion safety. Measure actual Pi hardware before
setting budgets; no synthetic performance targets are assumed.

## Recording integrity and offline recovery (0.11.9)

PiSD writes each JPEG, its full \`records.jsonl\` trace, its trainer-friendly
\`labels.jsonl\` row, and the session \`manifest.json\` in separate steps.
A crash, power loss, or full SD card may leave a partial JSONL tail, unmatched
metadata or a JPEG without a label.

**Inspect without changing recordings:**

\`\`\`bash
cd ~/PiDrive/PiSD
python3 scripts/recover_recordings.py 2026-11-22/SESSION_FOLDER
\`\`\`

This prints the valid record/label counts, matching pairs, missing rows,
orphan JPEGs, malformed/duplicate metadata and manifest-count mismatch.
The default command performs **no writes** and exits nonzero when an issue
still needs attention.

**Repair a stopped, copied or archived session explicitly:**

\`\`\`bash
python3 scripts/recover_recordings.py 2026-11-22/SESSION_FOLDER --repair --confirm-offline
\`\`\`

Stop recording and close any trainer or file writer first. Repair creates a
unique \`.recovery_backups/\` subfolder containing originals and an audit
report before replacing any metadata. It never deletes or relabels JPEGs,
rewrites valid original rows, or truncates malformed lines.

- A full trace record without a label may supply a missing trainer label.
- A label without a trace record may supply a **limited reconstructed record**
  explicitly marked as such. The unavailable original camera/motor telemetry
  is not fabricated.
- An orphan JPEG with neither record nor label is **reported only**; no
  steering or throttle is invented.
- When the operator confirms the session is offline, an interrupted
  \`running: true\` flag is cleared and the manifest's \`frame_count\` is
  reconciled to the number of complete record/label pairs. The true historical
  end time remains unknown; recovery does not make one up.
- A repeat repair does not duplicate recovered rows. If an individual file
  replacement fails, the preserved backups allow manual rollback.
- The original frame ID, JPEG filename convention, daily capture folders,
  AI labels and overlay sidecar formats are unchanged.

Repair is atomic **per metadata file**, not an all-file database transaction.
The \`--confirm-offline\` flag is an operator acknowledgement, not a kernel
lock against unpatched programs. Run it on a disposable copy first if a live
session is in doubt. You can load repaired \`labels.jsonl\` into piTrainer
using the existing session workflow. Retain \`.recovery_backups\` until the
recording has been reviewed.

## Stable baseline notes

`PiSD_0_11_0` is the original uploaded baseline; `PiSD_0_11_9` is the current forward patch on the `0_11_x` line.

It includes the tested service foundation from earlier baselines plus the accepted v6, v7, v8, v9, and v10-promotion Manual Drive, recording, overlay, AI Mode, steering algorithm, motor tuning reset, keyboard-control, safety-policy, AI-runtime, and validation cleanup patch lines.

Real wheel direction is intentionally configurable through settings because different cars may be wired differently. Use lifted-wheel motor channel tests before driving on the floor.


## PiSD 0.10.6 AI Mode manual-pad patch

`PiSD_0_10_6_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_5`. It does not promote a new stable rollback baseline.

AI Mode now has a three-way `Limiter / correction / manual` panel:

- `Limiter` keeps the saved AI output-mode, max throttle, max steering, fixed throttle, update-rate, and smoothing controls.
- `Correction` keeps the additive equation `AI + manual * Correction %`.
- `Manual pad` is a full manual takeover pad using drag input and arrow keys like Manual Drive. It sends direct guarded `/api/control/manual` commands and stops AI drive control.

The shared safety acknowledgement and motor-output enable controls now sit outside the toggled panes, so they remain visible whichever pane is selected. There is still only one `Save AI settings` button, in the panel header, outside the toggled pane content.

## Folder layout

```text
PiSD/
├── PiSD.py                       # main launcher
├── README.md                     # install/run overview
├── requirements.txt              # single pip dependency file
├── config/
│   └── defaults.json             # safe default camera/motor settings
├── pisd/
│   ├── __init__.py               # PiSD package version
│   ├── app.py                    # Flask GUI/API wiring
│   ├── web/                      # templates and static assets
│   ├── core/                     # errors/settings/value helpers
│   └── services/                 # camera, motor, recording, AI services and small AI math helpers
├── scripts/                      # validation and diagnostic scripts
├── test_outputs/                 # generated test captures/log-friendly outputs
├── docs/                         # architecture, testing, settings, and stable baseline notes
└── PATCH_NOTES/                  # historical patch notes and stable release notes
```

## Install / run on Raspberry Pi

From the PiDrive root:

```bash
cd ~/PiDrive
unzip -o PiSD_0_10_0.zip
cd ~/PiDrive/PiSD
python3 -m pip install --break-system-packages -r requirements.txt
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware  # requires PISD_ACCESS_TOKEN; see LAN setup below
```

Open from another device on the same network:

```text
http://<pi-ip>:5050
```

After applying the package over an older browser session, hard refresh the page:

```text
Ctrl + F5
```

## Standard validation

Container/desktop static validation:

```bash
python3 -m compileall -q pisd scripts
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
```

Pi hardware validation should also include:

```bash
python3 scripts/test_camera_service.py --hardware
python3 scripts/test_motor_service.py --hardware
python3 scripts/test_motor_channels.py --hardware
```

## Known limits / next steps

- Full Flask route/API tests were not run in the packaging container because Flask is not installed there.
- Real Raspberry Pi camera and motor hardware were not tested in the packaging container.
- Dashboard remains a labelled legacy/development comparison shell; Manual Drive and AI Mode are the active control pages.
- Shared API/status helper logic is still duplicated across some frontend files and can be centralised later.
- piTrainer still needs a matching update to redraw the overlay from saved `overlay_settings` metadata.
- Camera setting source-of-truth is still duplicated between backend defaults, service dataclass, UI forms, and diagnostic scripts. If the OV5647 colour still does not match the earlier 03/91 diagnostic result on real hardware, that should be a future `0_10_x` camera patch.




## PiSD 0.11.2 AI workflow settings and manual-release preview patch

`PiSD_0_11_2_patch.zip` builds forward from `PiSD_0_11_0` plus accepted `0_11_1`.

Changes:
- The `Confirm safe test + enable motors` checkbox now sits in the top AI workflow / Model-based driving panel.
- The AI workflow panel has a `Settings` button that opens an overlay popup for setting camera FPS. Applying the value uses `/api/camera/apply` and persists through the existing camera settings save path.
- Releasing the AI Mode Manual pad sends a motor-only stop with `keep_ai_preview`, so AI preview and the safe-output overlay continue running instead of being stopped.
- Global STOP and `STOP AI + motors` still stop AI and motors normally.

Rollback safety: this patch preserves the yellow Start AI preview/Snapshot/Record buttons, AI-safe recording labels, top-of-preview controls, original frame-id format, single confirmation semantics, Records & snaps panel, Space STOP, additive correction math, fixed-throttle mode, and max-throttle persistence.

## PiSD 0.11.1 AI preview/manual recording patch

`PiSD_0_11_1_patch.zip` builds forward from the current `PiSD_0_11_0` baseline.

Changes:
- AI Mode Manual pad no longer stops an active AI preview loop. Manual drag/keyboard input owns motor output, while the AI preview can keep updating the overlay from the latest safe AI command.
- If Manual pad is used while AI drive is active, AI motor output is switched back to preview before the manual command is applied.
- AI Mode snapshots and recordings now request `command_source: ai_safe_command`, so `labels.jsonl` stores the latest safe AI steering/throttle output while the full record still preserves the manual motor command trace.
- `Start AI preview`, `Snapshot`, and `Record` are styled as yellow preparatory actions.

Rollback safety: this patch preserves the single AI safety confirmation, top-of-preview controls, original frame-id format, Records & snaps panel, Space STOP, additive correction math, fixed-throttle mode, max-throttle persistence, and Manual pad motor gating.

## PiSD 0.11.0 AI text and one-confirmation patch

`PiSD_0_11_0_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_10`, starting the `0_11_x` forward patch line.

Changes:
- Shortened AI Mode help text so the page is less crowded.
- Replaced the two AI Mode safety/motor checkboxes with one visible confirmation: `Confirm safe test + enable motors`.
- The frontend still sends both backend guard fields, `safety_ack=true` and `enable_motor_output=true`, when the single confirmation is checked, so backend safety checks remain unchanged.

Rollback safety: this patch preserves Start live, top-of-preview buttons, AI snapshot/record shortcuts, Records & snaps, global Space STOP, additive correction math, fixed-throttle-after-correction, Manual pad takeover, max-throttle persistence, and the restored original frame-id format.

## PiSD 0.10.10 original frame-id restore patch

`PiSD_0_10_10_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_9`. It does not promote a new stable rollback baseline.

Changed behaviour:

- Recording image filenames are restored to the original shorter format: `frame_000001_<utc-stamp>_<uuid>.jpg`.
- `records.jsonl` frame IDs are restored to the original format: `<session_id>_000001_<utc-stamp>_<uuid>`.
- The experimental `frame_id_scheme` / `frame_id_unique_scope` fields from `0_10_9` are removed from new records and overlay history.
- `labels.jsonl` is restored to the original compact trainer-facing schema without the new global-id fields.
- The `0_10_9` preview-button placement fixes are preserved.

Known trade-off: this returns to the simpler original workflow, so frame identity is again mainly session-scoped in trainer-facing labels. Use `session_id`, `timestamp_utc`, and folder path if comparing frames across sessions.

Rollback safety: this patch preserves the accepted Start live workflow, top-of-preview buttons, AI snapshot/record shortcuts, Records & snaps, global Space STOP, additive correction math, fixed-throttle-after-correction, Manual pad takeover, and max-throttle persistence behaviour.

## PiSD 0.10.9 preview-button placement and global frame-id patch

`PiSD_0_10_9_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_8`. It does not promote a new stable rollback baseline.

Changed behaviour:

- Manual Drive keeps `Start live`, `Snapshot`, and `Record` above the camera preview frame.
- AI Mode keeps camera actions and AI run actions above the camera preview frame.
- The legacy Dashboard keeps its camera/live controls above the preview frame.
- The Testing Server GUI keeps diagnostic camera buttons above the preview image.
- Recording frame IDs now use `pisd_<session/date>_fNNNNNN_<utc-stamp>_<uuid>` and are also included in `labels.jsonl`, reducing merge collisions across different recording days/sessions.

Rollback safety: this patch preserves the accepted Start live workflow, AI snapshot/record shortcuts, Records & snaps, global Space STOP, additive correction math, fixed-throttle-after-correction, Manual pad takeover, and max-throttle persistence behaviour.

## PiSD 0.10.8 AI max-throttle persistence patch

`PiSD_0_10_8_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_7`. It does not promote a new stable rollback baseline.

Main UI/runtime update:

- AI Mode limiter settings now protect active edits from the 250 ms AI status refresh.
- `Max throttle` auto-saves after editing, so the value is not overwritten by the old saved/default value before the user can press Save.
- The other AI limiter controls also use the same dirty-field guard and auto-save path for consistency.
- Successful saves force the form to repaint from persisted settings only after the new values are confirmed.

Rollback safety: this patch preserves Start live, AI snapshot/record shortcuts, Records & snaps, global Space STOP, additive correction math, fixed-throttle-after-correction, and full Manual pad takeover behaviour.


## PiSD 0.10.7 AI recording panel and global Space STOP patch

`PiSD_0_10_7_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_6`. It does not promote a new stable rollback baseline.

Main UI/runtime update:

- AI Mode now has a `Records & snaps` panel using the same recording folder list, selected-folder summary, zip download, and safe delete workflow as Manual Drive.
- The shared recording helper lives in `pisd/web/static/js/recording_download_panel.js` so the AI page does not need to duplicate folder-management logic inside the large AI controller.
- Space is now a global STOP shortcut loaded by `pisd/web/static/js/global_space_stop.js`. On `/ai-mode`, it stops AI first and then sends motor STOP. On other pages, it sends motor STOP.
- AI Mode and Manual Drive listen for the shared `pisd:space-stop` event to reset their local pad/readout state after the global stop.

Rollback safety: this patch preserves the accepted Start live workflow, AI snapshot/record buttons and `r`/`s` shortcuts, additive correction equation, fixed-throttle-after-correction behaviour, and full Manual pad takeover mode.


### U28 camera-fault rearm (0.11.13)

The additive `safety` object in `GET /api/status` and `GET /api/ai/status` uses schema version 1, also available from `GET /api/safety/status`. If a camera-frame timeout latches during AI operation, stop AI and restore advancing camera frames. `POST /api/safety/rearm` with JSON `{"confirm":true}` clears that latch **only** after verifying a stopped AI worker, a newly arriving JPEG and a motor stop. AI start, manual nonzero output and motor test/tuning reject latched motion; STOP remains available. AI motor output still requires a fresh acknowledgement per start. Hardware verification required before deployment.

### Manual command lease (0.11.24)

Manual and AI-assist commands expire after 0.85 seconds without a new command or a valid renewal. The Manual Drive and AI Mode browser pages renew the current live command every 250 ms; STOP, page hide, focus loss and rejected renewal cancel the browser lease. The heartbeat endpoint never applies a new motor command; a rejected/expired lease needs new operator input. The legacy dashboard's one-shot drive buttons are intentionally bounded pulses, not persistent commands. API clients can renew a live command using its private `manual_lease_id` in `POST /api/control/heartbeat` (`{"lease_id":"…"}`); never log or persist the token. Existing clients not renewing stop automatically. No config migration. A watchdog is not a physical emergency relay; verify the Pi with wheels lifted and a reachable disconnect before deployment.

## LAN operator access (0.11.25)

Local-only mode remains the default (`python3 PiSD.py`); no token is required on loopback. For LAN use generate a random token (`python3 -c 'import secrets; print(secrets.token_hex(32))'`) and configure `PISD_ACCESS_TOKEN` in the process environment before launching. Never commit the token or put it into runtime JSON, URLs, command-line arguments or shared logs. For example, in Bash, enter the generated value without echoing: `read -rs PISD_ACCESS_TOKEN; export PISD_ACCESS_TOKEN; echo`, then run `python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware`. Restart the service after setting its environment. For an existing systemd service, add a root-readable environment file outside the repository via an EnvironmentFile override; keep its permissions at 0600. Without the token the existing 0.0.0.0 launch will deliberately fail before constructing services. Browser: open the Pi address and sign in once; the session uses a distinct HttpOnly SameSite=Strict cookie and is invalidated on server restart. API clients on LAN must send `Authorization: Bearer <token>`; browser mutations need same-origin metadata (Origin or Sec-Fetch-Site), including STOP and page-hide beacons. Older browsers without this metadata must be upgraded or use an authorized API client. Loopback scripts may continue JSON/empty-body requests without browser metadata. Local multipart/form clients without browser headers should use a token and bearer authentication or send a matching Origin. Front Page sign-out invokes STOP first and retains the session if STOP fails. The token protects the whole server, including camera streams, settings, recordings and model files. Plain HTTP does not encrypt credentials or traffic: use a trusted isolated LAN, SSH tunnel, or a properly configured HTTPS reverse proxy (set PISD_SESSION_SECURE=1 only for HTTPS; preserve the actual origin and do not expose the backend). Do not expose PiSD to the public internet. Re-authenticate after server restart. This is shared operator access, not multi-user permissions or a physical safety relay.

### Runtime configuration recovery (0.11.26)

Malformed `config/runtime_settings.json` is preserved byte-for-byte as a sibling `runtime_settings.json.corrupt-<digest>.bak` before replacement. The original stays in place until a successful settings save. Startup falls back to defaults only when the settings cannot be loaded; a later failed load retains the previous in-memory settings. Inspect the Settings recovery warning and local server log, then review the backup before restoring or explicitly saving new values. If the original cannot be read or a recovery copy cannot be verified, saving fails without replacing the original. Do not commit recovery files or delete them until recovery is confirmed. No migration of existing valid configuration is introduced.
