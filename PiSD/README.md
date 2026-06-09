# PiSD

`PiSD_0_10_11` patch package — builds forward from the `PiSD_0_10_0` stable v10 baseline plus accepted `0_10_1` through `0_10_10` UI/AI-correction/manual-pad/recording/persistence/layout patches.

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behaviour patterns, but PiServer files must not be overwritten by PiSD experiments.

Future bug-fix patches after this package should use `PiSD_0_10_x_patch` naming unless a newer stable line is promoted.

## Current version

`PiSD_0_10_11` patch package. `PiSD_0_10_0` remains the full stable v10 baseline built from the accepted `PiSD_0_9_0` stable package plus the accepted `0_9_1` through `0_9_10` patch line. It promotes the latest AI runtime/model compatibility work, AI update-rate/control-loop improvements, combined camera/live-stream control, AI Mode recording/snapshot controls, keyboard steering timing, overlay recording metadata, and dead-zone cleanup into a new rollback baseline.

Use `PiSD_0_10_0` as the rollback point for future PiSD work unless a newer stable line is promoted; this patch is the tenth `0_10_x` forward fix.

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
- AI Mode max throttle and fixed throttle controls allow full-scale `1.00`; Update Hz can be set up to `60` when the Pi/model can keep up.
- AI Mode preview reuses the Manual Drive preview-frame design, keeps Start live/Snapshot/Record and Start AI preview/Start AI drive/Stop AI above the camera view, and draws the road-guide overlay from the model prediction after the safety limiter.
- AI Mode `Limiter / correction / manual` panel has three panes: Limiter settings, additive AI Correction, and a full Manual pad takeover.
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

## Stable baseline notes

`PiSD_0_10_0` is the stable rollback baseline; `PiSD_0_10_11` is the current forward patch on the `0_10_x` line.

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
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
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



## PiSD 0.10.11 AI text and one-confirmation patch

`PiSD_0_10_11_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_10`. It does not promote a new stable rollback baseline.

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
