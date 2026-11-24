# PiServer

## R49 — Bounded recent operator events (0_4_28)

The existing Status dock now includes collapsed **Recent operator events** under
Startup preflight. Expand it and choose **Refresh events** for a read-only GET
`/api/recent-events`. **Copy events** copies the currently displayed sanitized
rows to the clipboard; when clipboard access is denied, select the visible
text manually. No telemetry or continuous polling runs.

The server keeps at most **128** entries in a thread-safe in-memory deque.
Its GET returns at most **80** entries. Each contains only a UTC timestamp,
constant operation/category/title, and `succeeded`, `failed`, `partial`
or `observed` outcome. The HTTP response hook records selected human
actions such as Camera/Motor Apply, model upload/load, recording, Save,
safety rearm, and **Emergency STOP**. The 60 ms manual drive command
endpoint is **excluded** to avoid excessive logging. R47
`correlation_id` remains on failures; the R49 ring does not copy failure
payloads, camera frames, exceptions, model paths, tokens or settings.

This is a volatile process-local event view; it resets on server restart.
The existing runtime, hardware stop latch, HTTP status and config
persistence are unchanged. The copy button is not a cloud exporter.

From repository root:
```bash
cd PiServer && python -m unittest discover -s tests -p 'test_recent_events_r49.py' -v
cd ..
node --test PiServer/tests/test_recent_events_ui_r49.cjs
```
Check real STOP/rearm, Save failures including `saved:false`, recording,
model loading, active camera/motor and browser clipboard behavior on a Pi.

## R48 passive startup preflight (0_4_27)

The existing Status dock has a **collapsed, read-only Startup preflight**.
On page load (and on **Refresh checks**), the browser sends **GET**
`/api/preflight` only. The endpoint reads already-running camera, motor,
model and safety service getters plus `shutil.disk_usage` for the PiServer
project volume. It does **not** start or stop motors/camera, load a model,
probe another device, restart a service or save/reset settings.

The six checks cover service mode, camera backend, AI model, GPIO motor
adapter/safety latch, disk free space and browser-to-PiServer HTTP reachability.
**Simulation** is explicitly separate from hardware adapter presence;
**adapter detected** does *not* certify safe motor output or fresh camera
frames. "Network observed" means only this HTTP GET reached PiServer,
not that Wi-Fi/router or internet access works. Unknown disk data is shown
without exporting any absolute file path or exception text.

Commands from the repository root:
```bash
cd PiServer
python -m unittest discover -s tests -p 'test_preflight_r48.py' -v
cd ..
node --test PiServer/tests/test_preflight_ui_r48.cjs
```
The R48 Python checks import the pure formatter (no Flask, motor or camera
initialization). On the real Pi, confirm behavior in hardware, simulation,
low-disk and missing-model states, and confirm moving the car is impossible
through the preflight UI. Existing STOP and Apply controls are unchanged.

## R47 failed-operation trace references (0_4_26)

A failed `POST`/`PUT`/`PATCH`/`DELETE` to `/api/*` returns its
original HTTP status and JSON fields **plus** `correlation_id` (16 server-
generated hexadecimal characters) and `operation` (safe server endpoint
name). The response also includes `X-Correlation-ID`. This covers legacy
`HTTP 200 + ok:false` and `saved:false` failures; successes do not get
a new trace ID. One log line per failed mutation is emitted with
`api_mutation_failure id=<ID> operation=<name> http_status=<status>`.
Look up the displayed reference in the PiServer process log; never paste
passwords, bearer tokens, full request bodies or arbitrary paths into the
diagnostic log.

Camera/Motor Apply now shows a short error and collapsible **Error details**
containing only ID, endpoint, HTTP status and safe error code. Login/CSRF
enforcement and saved settings readback are unchanged. The tracing hook
redacts credentials and absolute/explicit file paths in the failure
`message`/`error` diagnostic fields, not legitimate successful model/config
responses. No remote telemetry or persistent event storage is added.

Regression checks (from repo root):
```bash
python -m unittest discover -s PiServer/tests -p 'test_request_trace_r47.py' -v
node --test PiServer/tests/test_request_trace_ui_r47.cjs
```
The Python suite uses a hardware-free Flask response stand-in, so it does
not create motors or camera services. Check login 401/403, failed Apply,
backend restart, and actual browser Error details on the real Pi before
merging a draft.

## R45 visual style contract (0_4_24)

New web panels should follow [UI_DESIGN_TOKENS.md](UI_DESIGN_TOKENS.md):
semantic status colors, compact spacing, concise STOP/Apply labels, and
icon-size guidance. The real CSS/theme engine and the existing
`PiServerStyleCustom:v0_3_5` preference key are unchanged. Run
`node --test PiServer/tests/test_ui_style_tokens_r45.cjs` from repo root.
This is a design-policy/smoke-test update, not a layout reset.

## Adaptive status polling and bandwidth (0_4_23, R43)

The PiServer web UI still uses its R30 single-in-flight, decoded-JPEG,
sequence-checked camera preview, and the separate **60 ms** manual-control
tick remains unchanged. R43 schedules **read-only status** requests adaptively:

- **Active** (camera preview live, recording, manual input or pressed controls):
  status every **800 ms**, the previous period.
- **Idle, visible**: status every **2,500 ms**.
- **Hidden tab**: **zero periodic HTTP status requests**; the timer checks
  visibility every 5 seconds without a fetch. The existing visibility
  handler still issues a best-effort zero motor command as appropriate.
- **Failures**: exponential retry capped at **8,000 ms**; a visible-tab
  return triggers an immediate refresh and resets backoff on success.
  Only one status request may be in flight.

The backend now publishes the additive `server_status_at_ms` field, showing
its actual generation time in the existing status banner tooltip. The camera
preview continues to use backend `X-Preview-Seq` and `X-Preview-Live`
headers, not browser cache timestamps, to determine frame freshness.

**Modeled traffic profile, one visible idle tab for 60 seconds (status only):**
before 800 ms = **75 requests/min**; after 2,500 ms = **24 requests/min**,
a **68% reduction**. Active status remains 75/min. This is a deterministic
schedule calculation, **not a measured browser/network capture**. Failed
requests and control actions change realized counts.

Run `node --test PiServer/tests/test_adaptive_polling_r43.cjs` at the
repository root. For release, capture browser Network requests and frame
bytes for 60 seconds each in active, idle, hidden and tab-return states;
ensure real motor STOP/watchdog and video freshness are unchanged.

## Model compatibility and rollback (0.4.17, U27)

PiServer checks optional adjacent `<model>.tflite.manifest.json`
files before model activation. Manifests identify the
`steering_control` family, SHA-256 checksum, RGB/NHWC geometry,
normalization, ordered steering/throttle outputs, quantization mode
and optional training seed. A present incompatible manifest causes a
clear failure while the existing interpreter stays active.

The existing TensorFlow Lite signature and zero-input inference preflight
remains mandatory even for manifest-bearing models. Sidecar-free older
models still load after tensor preflight, with a legacy warning. The
authenticated model-upload API accepts an optional multipart
`manifest` file; unverified or mismatched metadata cannot be attached
to an uploaded model. Existing model filenames are not overwritten by
upload, protecting a working model from accidental replacement.

`/api/model/list` and `/api/model/load` return `model_metadata`
with the active sidecar (or legacy warning). Deleting a model removes its
adjacent sidecar. The accepted LAN token/CSRF protections, motor watchdog,
camera/AI timings, storage guard and configuration behavior remain intact.
Real Pi 4 and end-to-end model swap tests are still required.

PiServer is the modular PiCar runtime backend/web UI for manual driving, recording, model management, camera operations, and control-loop orchestration.

## PiServer 0.4.16 — Recording disk-space protection (U26)

PiServer recording and snapshots now check available filesystem capacity
before creating sessions and images. The defaults are a **512 MiB low-space
warning** and a **256 MiB critical reserve**, plus estimated image write
size. Configure with environment variables (no changes to `runtime.json`):

```bash
export PISERVER_RECORDING_WARN_FREE_MB=512
export PISERVER_RECORDING_MIN_FREE_MB=256
```

The authenticated `GET /api/status` includes `recording_storage`: free and
total bytes, warning/critical thresholds, state, session size and up to five
recent failed writes. Per-session listing adds `size_bytes`. The last queried session size is cached for two seconds; explicit folder
listings inspect each selected folder. Size scans run outside recorder locks.

If space is critical, the recorder refuses to start or save images. If a
camera image write or JSONL append fails, only the recording is stopped:
the control loop, manual-command watchdog, e-stop, and live camera processing
continue unchanged. The recorder does not silently restart after free space
returns. Any partial metadata from a true disk-full interruption should be
reviewed manually before training.

**Cleanup is never automatic.** The existing recordings browser prompts for
confirmation and the authenticated delete endpoint additionally requires
`{"session":"SESSION_NAME","confirm":true}`. Only the selected inactive
folder can be deleted; historical sessions are never selected for pruning by
disk usage. Back up sessions before deletion. Do not lower the critical
reserve without validating your SD card capacity on hardware.

## PiServer 0.4.15 — Runtime latency diagnostics (U23)

The protected `GET /api/status` response now includes
`performance_diagnostics` with `controller`, `camera`, `model`, and
`camera_frame_age_s`. Controller metrics cover loop work and motor calls;
camera measures capture-loop work and dropped frames; model measures RGB
resize/preprocessing, inference and output postprocessing. Stage summaries
are bounded rolling p50/p95/last in milliseconds (120 samples maximum).
Missing stages have no measurements and are omitted rather than reported as
zero. The process CPU percentage is measured using process CPU time on status
reads, not whole-device CPU utilization; values above 100% are possible.

All measurements are memory-only, no log/SD writes or hardware dependencies
are added. This keeps prior 0.4.11 watchdog, 0.4.12 login protection,
0.4.13 model preflight, and 0.4.14 hardware ownership unchanged. A remote
client must authenticate before requesting status. No queue delay is claimed
where the code lacks a timestamped queue boundary; capture-to-motor latency
requires hardware time correlation and remains a follow-up. Performance
budgets must be measured on actual Pi 4 hardware, not guessed.

## Quick start

```bash
cd PiServer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python server.py
```

Python 3.11 is recommended. The core install supports the hardware-free
runtime; on Raspberry Pi OS install Picamera2/libcamera and the appropriate
GPIO backend through the OS. Use a separate `--system-site-packages` virtual
environment when those OS bindings are required. `requirements-pi.txt`
is an optional rpi-lgpio alternative to RPi.GPIO, not a second simultaneous
GPIO implementation. A compatible TFLite interpreter is separately optional
(`tflite-runtime`, or the TensorFlow fallback implemented by model_service.py).
Use `requirements-dev.txt` for tests. NumPy/OpenCV constraints follow the
hardware-free test matrix; confirm the OS camera ABI on the target device.
Existing systemd deployments are not migrated by these instructions.

### Access protection (0.4.12)

**Default (no token): localhost-only.** Open `http://127.0.0.1:5000` from the Pi itself.
Remote/LAN requests are also rejected at the Flask layer if a different WSGI
server accidentally exposes the application. An explicit non-loopback
`PISERVER_HOST` without a token causes startup to fail.

**Enable LAN control with an access token (32+ characters):**

```bash
cd PiServer
export PISERVER_ACCESS_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python server.py
```

Open `http://<pi-ip>:5000/login` and enter the token from the Pi terminal.
The browser keeps an HTTP-only, SameSite=Strict session cookie; it does **not**
store the access token in browser localStorage or put it in a URL. State-changing
browser requests require a CSRF token. The login expires on server restart
unless you configure a persistent `PISERVER_SESSION_SECRET`.

For service startup, store `PISERVER_ACCESS_TOKEN` in a private environment file
with permissions `0600` and add a matching `EnvironmentFile=` to the existing
systemd service override. **Do not commit the token or save it to runtime.json.**
An example using a shell-exported variable is shown above only for testing.

For programmatic API clients, supply the token as an HTTP header:

```text
Authorization: Bearer <access-token>
```

Bearer requests are authenticated but do not require the browser's CSRF token.
All routes, including the video feed, status, downloads, model management,
settings, and motor commands, require authorization when LAN mode is enabled.

**Security scope:** plain HTTP is not encrypted; a token can be intercepted on
an untrusted LAN. Use a trusted isolated network or a correctly configured HTTPS
reverse proxy/VPN. Do not expose port 5000 directly to the public Internet.
`PISERVER_SESSION_SECURE=1` enables Secure session cookies when using HTTPS;
leave it unset when accessing directly over HTTP. `PISERVER_HOST` can restrict
the listening interface even when a token is set. `PISERVER_PORT` defaults to 5000.


### Physical hardware ownership (0.4.14)

PiServer and CustomDrive reuse the same `piserver.services.camera_service` and
`piserver.services.motor_service` implementations. On a Raspberry Pi, they
now acquire a **nonblocking, shared-process camera/motor lease** before opening
physical camera or GPIO resources. Only one process may control the hardware.

- The default lock file is `/tmp/pidrive-physical-hardware.lock`.
- Both applications must use the **same path and filesystem**. If needed,
  set `PIDRIVE_HARDWARE_LOCK_FILE` to the same **absolute path** in both service
  environments. Never delete an in-use lock file to bypass the guard.
- If another process owns the hardware, the second process fails with an
  explicit error and **does not open its motor GPIO adapter**.
- Closing the motor first writes zero speed and calls GPIO cleanup before
  releasing its ownership. A camera capture thread that cannot stop retains
  its lease; restart is blocked until it has exited.
- A new motor instance starts its PWM outputs at **zero**. No previous motor
  command is restored; a new operator action is required to move the car.
- Desktop/simulation mode without Raspberry Pi hardware remains available.
  CustomDrive's existing `live` runtime factory can report why it fell back
  to simulation when hardware is busy. Mission 1 direct startup fails closed.

This is a **software advisory lock**, not a motor driver watchdog or
hardware emergency cutoff. An unpatched PiSD runtime or third-party GPIO
script that does not honor the same lease could still contend. A kill/power
failure can release the software lock before a physical motor output stops,
so validate hardware stop behavior separately. For a deliberate handover,
stop and close the current runtime, verify motors are stationary, then start
the other runtime. Use wheels raised for first testing.

## Current snapshot code markers

- App version constant: `piserver/app.py`
- Layout/localStorage namespace keys: `piserver/web/static/app.js`

Always align release docs to these files (not patch-note filenames alone).

## Runtime architecture

- Flask web app + MJPEG streaming endpoints
- modular services (camera, motor, recording, algorithms, runtime state)
- dock-style web workspace with per-page panel layouts
- runtime config save/reload support

## Optional Pi-only dependencies

- `picamera2`
- `RPi.GPIO`
- `tflite-runtime`

If unavailable, PiServer may run with simulated/fallback behavior depending on service.

## Key files

- Entry point: `server.py`
- Runtime config: `config/runtime.json`
- Backend wiring: `piserver/app.py`
- Front-end UI: `piserver/web/templates/index.html`
- Front-end logic: `piserver/web/static/app.js`
- Front-end styles: `piserver/web/static/styles.css`

## Systemd auto-start (optional)

```bash
sudo cp boot/pi_server.service /etc/systemd/system/pi_server.service
sudo systemctl daemon-reload
sudo systemctl enable pi_server.service
sudo systemctl restart pi_server.service
```

Adjust `WorkingDirectory`/`ExecStart` in the service file to match your install path.

## Bug-prevention reference

For layout versioning and compact-UI regression prevention practices, see:
- `../BUG_PREVENTION_NOTES.md`


### U28 safety status and explicit rearm (0_4_18)

The existing `GET /api/status` includes an additive `safety` object (schema version 1). `GET /api/safety/status` returns the same object. After E-stop, send `POST /api/safety/rearm` with `{"confirm":true}` under the existing PiServer LAN authentication and CSRF requirements. The legacy E-stop toggle `{"enabled":false,"confirm":true}` uses the same checked rearm path; `{"enabled":false}` is refused. Successful rearm zeros motor commands, switches to manual mode, and does **not** resume prior motion. Retest on Pi hardware before production use.

## Runtime configuration recovery (0_4_30)

Malformed `config/runtime.json` is copied byte-for-byte into a private sibling `runtime.json.corrupt-<digest>.bak`; the original is not replaced until a successful save. Startup with an unreadable configuration uses defaults; a failed reload of a running service retains its effective settings and refuses to reapply defaults. The Status dock displays a recovery warning, with full local paths in the server log. Save refuses to replace unreadable data or malformed data without a verified backup. Review the recovery file before relying on fallback settings. Valid unknown keys are retained when saving runtime snapshots. Do not commit recovery files or remove them before recovery is confirmed.
