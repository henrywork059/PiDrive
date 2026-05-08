from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pisd import __version__
from pisd.services.camera_service import CameraService
from pisd.services.motor_service import MotorService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = PROJECT_ROOT / "config" / "defaults.json"


def load_defaults() -> dict[str, Any]:
    try:
        with DEFAULTS_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def create_app(hardware_enabled: bool = False):
    try:
        from flask import Flask, Response, jsonify, render_template_string, request
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Flask is not installed. Run: python -m pip install -r requirements.txt") from exc

    defaults = load_defaults()
    camera_service = CameraService(defaults.get("camera"), hardware_enabled=hardware_enabled)
    motor_service = MotorService(defaults.get("motor"), hardware_enabled=hardware_enabled)

    app = Flask(__name__)
    app.config["pisd_services"] = {"camera": camera_service, "motor": motor_service}

    def build_status() -> dict[str, Any]:
        return {
            "app": "PiSD",
            "version": __version__,
            "hardware_requested": bool(hardware_enabled),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "camera": camera_service.status(),
            "motor": motor_service.status(),
        }

    @app.get("/")
    def index():
        return render_template_string(INDEX_HTML, status=json.dumps(build_status(), indent=2))

    @app.get("/api/status")
    def api_status():
        return jsonify(build_status())

    @app.post("/api/camera/start")
    def api_camera_start():
        ok, message = camera_service.start()
        return jsonify({"ok": ok, "message": message, "camera": camera_service.status()})

    @app.post("/api/camera/stop")
    def api_camera_stop():
        ok, message = camera_service.stop()
        return jsonify({"ok": ok, "message": message, "camera": camera_service.status()})

    @app.get("/api/camera/config")
    def api_camera_config():
        return jsonify({"ok": True, "config": camera_service.get_config()})

    @app.post("/api/camera/apply")
    def api_camera_apply():
        data = request.get_json(silent=True) or {}
        ok, message, config = camera_service.apply_settings(data, restart=True)
        return jsonify({"ok": ok, "message": message, "config": config})

    @app.get("/api/camera/frame.jpg")
    def api_camera_frame():
        frame = camera_service.get_jpeg_frame()
        if frame is None:
            camera_service.start()
            frame = camera_service.get_jpeg_frame()
        if frame is None:
            return jsonify({"ok": False, "message": "No frame available yet."}), 503
        return Response(frame, mimetype="image/jpeg", headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/video_feed")
    def video_feed():
        def generate():
            camera_service.start()
            last = None
            while True:
                frame = camera_service.get_jpeg_frame()
                seq = camera_service.status().get("frame_seq")
                if frame is not None and seq != last:
                    last = seq
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/motor/config")
    def api_motor_config():
        return jsonify({"ok": True, "config": motor_service.get_config()})

    @app.post("/api/motor/apply")
    def api_motor_apply():
        data = request.get_json(silent=True) or {}
        config = motor_service.apply_settings(data)
        return jsonify({"ok": True, "config": config})

    @app.post("/api/control/manual")
    def api_control_manual():
        data = request.get_json(silent=True) or {}
        left, right = motor_service.update(
            steering=data.get("steering", 0.0),
            throttle=data.get("throttle", 0.0),
            steer_mix=data.get("steer_mix"),
        )
        return jsonify({"ok": True, "left": left, "right": right, "motor": motor_service.status()})

    @app.post("/api/control/stop")
    def api_control_stop():
        motor_service.stop()
        return jsonify({"ok": True, "message": "Motors stopped.", "motor": motor_service.status()})

    @app.teardown_appcontext
    def cleanup(_exc):
        # Do not close on every request; Flask calls teardown after requests. Cleanup is handled by atexit.
        return None

    return app


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PiSD Hardware Service Sandbox</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #111827; color: #e5e7eb; }
    header, main { max-width: 1100px; margin: auto; padding: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
    .card { background: #1f2937; border: 1px solid #374151; border-radius: 14px; padding: 1rem; }
    button { border: 0; border-radius: 10px; padding: 0.65rem 0.9rem; cursor: pointer; margin: 0.2rem; }
    input[type=range] { width: 100%; }
    img { width: 100%; border-radius: 12px; background: #000; min-height: 160px; object-fit: contain; }
    pre { white-space: pre-wrap; overflow: auto; background: #030712; border-radius: 10px; padding: 0.75rem; font-size: 0.85rem; }
    .danger { background: #dc2626; color: white; }
    .primary { background: #2563eb; color: white; }
    .muted { background: #4b5563; color: white; }
  </style>
</head>
<body>
<header>
  <h1>PiSD Hardware Service Sandbox</h1>
  <p>Clean PiServer rebuild area with camera and motor services patched in behind safe API endpoints.</p>
</header>
<main class="grid">
  <section class="card">
    <h2>Camera</h2>
    <img id="preview" src="/api/camera/frame.jpg" alt="Camera preview">
    <p>
      <button class="primary" onclick="post('/api/camera/start')">Start camera</button>
      <button class="muted" onclick="post('/api/camera/stop')">Stop camera</button>
    </p>
  </section>
  <section class="card">
    <h2>Manual motor control</h2>
    <label>Steering <span id="steeringOut">0.00</span></label>
    <input id="steering" type="range" min="-1" max="1" value="0" step="0.01" oninput="sendControl()">
    <label>Throttle <span id="throttleOut">0.00</span></label>
    <input id="throttle" type="range" min="-1" max="1" value="0" step="0.01" oninput="sendControl()">
    <p><button class="danger" onclick="stopMotors()">STOP</button></p>
  </section>
  <section class="card">
    <h2>Status</h2>
    <pre id="status">{{ status }}</pre>
  </section>
</main>
<script>
async function post(url, body = {}) {
  const res = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  await refreshStatus();
  return res.json();
}
async function refreshStatus() {
  const res = await fetch('/api/status', {cache: 'no-store'});
  const data = await res.json();
  document.getElementById('status').textContent = JSON.stringify(data, null, 2);
}
let pending = false;
async function sendControl() {
  if (pending) return;
  pending = true;
  const steering = Number(document.getElementById('steering').value);
  const throttle = Number(document.getElementById('throttle').value);
  document.getElementById('steeringOut').textContent = steering.toFixed(2);
  document.getElementById('throttleOut').textContent = throttle.toFixed(2);
  try { await post('/api/control/manual', {steering, throttle}); } finally { pending = false; }
}
async function stopMotors() {
  document.getElementById('steering').value = 0;
  document.getElementById('throttle').value = 0;
  document.getElementById('steeringOut').textContent = '0.00';
  document.getElementById('throttleOut').textContent = '0.00';
  await post('/api/control/stop');
}
setInterval(() => {
  const img = document.getElementById('preview');
  img.src = '/api/camera/frame.jpg?t=' + Date.now();
  refreshStatus();
}, 1000);
</script>
</body>
</html>
"""
