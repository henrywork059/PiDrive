# PiServer

PiServer is the modular PiCar runtime backend/web UI for manual driving, recording, model management, camera operations, and control-loop orchestration.

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
pip install -r requirements.txt
python server.py
```

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
