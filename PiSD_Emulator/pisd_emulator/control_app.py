"""Browser control workspace for PiSD Emulator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

from .engine import TRACKS
from .runtime import PiSDRuntime


WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def create_control_app(runtime: PiSDRuntime) -> Flask:
    app = Flask(__name__)
    trusted_origin = f"http://127.0.0.1:{runtime.control_port}"

    @app.before_request
    def local_control_only():
        # The controller is a privileged local origin; reject rebinding and CSRF.
        if request.remote_addr != "127.0.0.1" or request.host_url.rstrip("/") != trusted_origin:
            return jsonify(ok=False, error="Local emulator origin required."), 403
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            site = request.headers.get("Sec-Fetch-Site")
            if (origin is not None and origin != trusted_origin) or (site is not None and site != "same-origin") or not request.is_json:
                return jsonify(ok=False, error="Cross-origin emulator control denied."), 403

    @app.after_request
    def controller_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/assets/<path:filename>")
    def assets(filename: str):
        return send_from_directory(WEB_DIR / "assets", filename)

    @app.get("/scenarios")
    def scenarios():
        return send_from_directory(WEB_DIR, "scenarios.html")

    @app.post("/api/scenarios/replay")
    def replay():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or "source" not in data:
            return jsonify(ok=False, error="Supply source (null for generated camera)."), 400
        try:
            return jsonify(runtime.configure_replay(data["source"], data.get("loop", False)))
        except (ValueError, TypeError, OSError) as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post("/api/scenarios/camera-fault")
    def camera_fault():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or type(data.get("active")) is not bool:
            return jsonify(ok=False, error="Supply boolean active."), 400
        try:
            return jsonify(runtime.set_camera_fault(data["active"]))
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.get("/api/status")
    def status():
        return jsonify(runtime.status())

    @app.get("/api/pisd/status")
    def pisd_status():
        return jsonify(runtime.pisd_status())

    @app.post("/api/runtime/start")
    def start_runtime():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(runtime.start(data.get("port")))
        except Exception as exc:
            return jsonify({"ok": False, "error": f"{type(exc).__name__}: {exc}", "status": runtime.status()}), 400

    @app.post("/api/runtime/stop")
    def stop_runtime():
        return jsonify(runtime.stop())

    @app.post("/api/runtime/restart")
    def restart_runtime():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(runtime.restart(data.get("port")))
        except Exception as exc:
            return jsonify({"ok": False, "error": f"{type(exc).__name__}: {exc}", "status": runtime.status()}), 400

    @app.post("/api/vehicle/reset")
    def reset_vehicle():
        runtime.reset_vehicle()
        return jsonify(runtime.status())

    @app.post("/api/track")
    def set_track():
        data = request.get_json(silent=True) or {}
        track_id = str(data.get("track_id", "straight"))
        if track_id not in TRACKS:
            return jsonify({"ok": False, "error": "Unknown track."}), 400
        runtime.change_track(track_id)
        return jsonify(runtime.status())

    @app.post("/api/simulation/pause")
    def pause_simulation():
        data = request.get_json(silent=True) or {}
        runtime.engine.set_paused(bool(data.get("paused", True)))
        return jsonify(runtime.status())

    @app.post("/api/simulation/step")
    def step_simulation():
        data = request.get_json(silent=True) or {}
        count = max(1, min(600, int(data.get("steps", 1))))
        runtime.engine.step(count)
        return jsonify(runtime.status())

    @app.post("/api/simulation/speed")
    def set_simulation_speed():
        data = request.get_json(silent=True) or {}
        speed = runtime.engine.set_speed_scale(data.get("scale", 1.0))
        return jsonify({"speed_scale": speed, **runtime.status()})

    @app.post("/api/simulation/settings")
    def save_simulation_settings():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(runtime.update_simulation_settings(data))
        except Exception as exc:
            return jsonify({"ok": False, "error": f"{type(exc).__name__}: {exc}"}), 400

    @app.get("/api/camera.jpg")
    def camera_frame():
        current_app = runtime._app
        if current_app is None:
            return jsonify({"ok": False, "error": "Start PiSD Emulator to receive frames."}), 503
        camera = current_app.config["pisd_services"]["camera"]
        jpeg = camera.get_jpeg_frame()
        if not jpeg:
            return jsonify({"ok": False, "error": "PiSD camera is warming up."}), 503
        from flask import Response

        return Response(jpeg, mimetype="image/jpeg", headers={"Cache-Control": "no-store, max-age=0"})

    return app


__all__ = ["create_control_app"]
