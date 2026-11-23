# PiServer

PiServer is the modular PiCar runtime backend/web UI for manual driving, recording, model management, camera operations, and control-loop orchestration.

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
