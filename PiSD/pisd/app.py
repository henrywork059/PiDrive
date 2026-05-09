from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pisd import __version__
from pisd.core.errors import ErrorReporter, PiSDErrorCodes, ok_payload, report_payload
from pisd.services.camera_service import CameraService
from pisd.services.motor_service import MotorService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = PROJECT_ROOT / "config" / "defaults.json"
APP_ERRORS = ErrorReporter("app")


def load_defaults() -> dict[str, Any]:
    try:
        with DEFAULTS_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            APP_ERRORS.report(
                PiSDErrorCodes.APP_CONFIG_LOAD_FAILED,
                "config/defaults.json did not contain a JSON object; using empty defaults.",
                severity="warning",
                context={"path": str(DEFAULTS_PATH)},
            )
            return {}
        return data
    except Exception as exc:
        APP_ERRORS.report(
            PiSDErrorCodes.APP_CONFIG_LOAD_FAILED,
            f"Failed to load config/defaults.json; using empty defaults: {exc}",
            severity="warning",
            context={"path": str(DEFAULTS_PATH)},
            exc=exc,
        )
        return {}


def create_app(hardware_enabled: bool = False):
    try:
        from flask import Flask, Response, jsonify, render_template_string, request
    except ImportError as exc:  # pragma: no cover
        APP_ERRORS.report(
            PiSDErrorCodes.APP_DEPENDENCY_MISSING,
            "Flask is not installed. Run: python -m pip install -r requirements.txt",
            exc=exc,
        )
        raise RuntimeError(
            f"{PiSDErrorCodes.APP_DEPENDENCY_MISSING}: Flask is not installed. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc

    defaults = load_defaults()
    camera_service = CameraService(defaults.get("camera"), hardware_enabled=hardware_enabled)
    motor_service = MotorService(defaults.get("motor"), hardware_enabled=hardware_enabled)

    app = Flask(__name__)
    app.config["pisd_services"] = {"camera": camera_service, "motor": motor_service}
    app.config["pisd_errors"] = APP_ERRORS

    def all_errors(limit: int = 10) -> dict[str, Any]:
        return {
            "app": APP_ERRORS.history(limit=limit),
            "camera": camera_service.errors.history(limit=limit),
            "motor": motor_service.errors.history(limit=limit),
        }

    def build_status() -> dict[str, Any]:
        return {
            "app": "PiSD",
            "version": __version__,
            "hardware_requested": bool(hardware_enabled),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "code": PiSDErrorCodes.OK,
            "camera": camera_service.status(),
            "motor": motor_service.status(),
            "errors": all_errors(limit=5),
        }

    def get_json_payload() -> tuple[dict[str, Any], Any | None]:
        if not request.data:
            return {}, None
        data = request.get_json(silent=True)
        if data is None:
            report = APP_ERRORS.report(
                PiSDErrorCodes.API_INVALID_JSON,
                "Request body was not valid JSON.",
                context={"path": request.path},
            )
            return {}, report
        if not isinstance(data, dict):
            report = APP_ERRORS.report(
                PiSDErrorCodes.API_INVALID_JSON,
                "JSON payload must be an object.",
                context={"path": request.path, "payload_type": type(data).__name__},
            )
            return {}, report
        return data, None

    @app.get("/")
    def index():
        return render_template_string(INDEX_HTML, status=json.dumps(build_status(), indent=2))

    @app.get("/api/status")
    def api_status():
        return jsonify(build_status())

    @app.get("/api/errors")
    def api_errors():
        return jsonify(ok_payload("Recent PiSD error reports.", errors=all_errors(limit=25)))

    @app.post("/api/errors/clear")
    def api_errors_clear():
        APP_ERRORS.clear()
        camera_service.errors.clear()
        motor_service.errors.clear()
        return jsonify(ok_payload("Error history cleared."))

    @app.post("/api/camera/start")
    def api_camera_start():
        try:
            ok, message = camera_service.start()
            report = camera_service.errors.latest() if camera_service.last_error else None
            return jsonify(report_payload(ok, report, message, camera=camera_service.status()))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera start API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.post("/api/camera/stop")
    def api_camera_stop():
        try:
            ok, message = camera_service.stop()
            report = camera_service.errors.latest() if camera_service.last_error else None
            return jsonify(report_payload(ok, report, message, camera=camera_service.status()))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera stop API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.get("/api/camera/config")
    def api_camera_config():
        return jsonify(ok_payload("Camera config loaded.", config=camera_service.get_config()))

    @app.post("/api/camera/apply")
    def api_camera_apply():
        data, json_error = get_json_payload()
        if json_error is not None:
            return jsonify(report_payload(False, json_error)), 400
        try:
            ok, message, config = camera_service.apply_settings(data, restart=True)
            report = camera_service.errors.latest() if not ok else None
            return jsonify(report_payload(ok, report, message, config=config))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera apply API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.get("/api/camera/frame.jpg")
    def api_camera_frame():
        try:
            frame = camera_service.get_jpeg_frame()
            if frame is None:
                camera_service.start()
                frame = camera_service.get_jpeg_frame()
            if frame is None:
                report = camera_service._record(  # internal service helper used to keep status and API code aligned
                    PiSDErrorCodes.CAMERA_NO_FRAME,
                    "No JPEG camera frame is available yet.",
                    context={"path": request.path},
                )
                return jsonify(report_payload(False, report)), 503
            return Response(frame, mimetype="image/jpeg", headers={"Cache-Control": "no-store, max-age=0"})
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera frame API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

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
        return jsonify(ok_payload("Motor config loaded.", config=motor_service.get_config()))

    @app.post("/api/motor/apply")
    def api_motor_apply():
        data, json_error = get_json_payload()
        if json_error is not None:
            return jsonify(report_payload(False, json_error)), 400
        try:
            config = motor_service.apply_settings(data)
            report = motor_service.errors.latest() if motor_service.last_error else None
            return jsonify(report_payload(True, report, "Motor settings applied.", config=config))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Motor apply API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.post("/api/control/manual")
    def api_control_manual():
        data, json_error = get_json_payload()
        if json_error is not None:
            return jsonify(report_payload(False, json_error)), 400
        try:
            left, right = motor_service.update(
                steering=data.get("steering", 0.0),
                throttle=data.get("throttle", 0.0),
                steer_mix=data.get("steer_mix"),
            )
            report = motor_service.errors.latest() if motor_service.last_error else None
            return jsonify(report_payload(True, report, "Manual motor command applied.", left=left, right=right, motor=motor_service.status()))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Manual control API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.post("/api/control/stop")
    def api_control_stop():
        try:
            motor_service.stop()
            report = motor_service.errors.latest() if motor_service.last_error else None
            return jsonify(report_payload(True, report, "Motors stopped.", motor=motor_service.status()))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Motor stop API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.errorhandler(404)
    def api_not_found(_exc):
        report = APP_ERRORS.report(PiSDErrorCodes.API_NOT_FOUND, f"Route not found: {request.path}", context={"path": request.path})
        return jsonify(report_payload(False, report)), 404

    @app.errorhandler(Exception)
    def api_unhandled(exc):
        report = APP_ERRORS.report(PiSDErrorCodes.API_UNHANDLED_EXCEPTION, f"Unhandled API exception: {exc}", exc=exc)
        return jsonify(report_payload(False, report)), 500

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
