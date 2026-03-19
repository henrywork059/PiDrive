from __future__ import annotations

import atexit
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .runtime_factory import create_runtime

WEB_DIR = Path(__file__).resolve().parent / "web"


def create_app(mode: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    runtime = create_runtime(mode=mode, max_cycles=2)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def api_status():
        payload = runtime.status()
        payload["mode_requested"] = getattr(runtime, "mode_requested", payload.get("mode", "sim"))
        payload["fallback_reason"] = getattr(runtime, "fallback_reason", "")
        return jsonify(payload)

    @app.route("/api/frame.jpg")
    def api_frame_jpg():
        get_jpeg = getattr(runtime, "get_jpeg_frame", None)
        if not callable(get_jpeg):
            return ("", 204)
        frame = get_jpeg()
        if frame is None:
            return ("", 204)
        response = Response(frame, mimetype="image/jpeg")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/api/settings")
    def api_settings():
        getter = getattr(runtime, "get_settings", None)
        if not callable(getter):
            return jsonify({"ok": False, "message": "Runtime settings are unavailable."}), 404
        return jsonify({"ok": True, "settings": getter()})

    @app.route("/api/settings", methods=["POST"])
    def api_settings_save():
        saver = getattr(runtime, "save_settings", None)
        if not callable(saver):
            return jsonify({"ok": False, "message": "Runtime settings are unavailable."}), 404
        data = request.get_json(silent=True) or {}
        saved = saver(data)
        return jsonify({"ok": True, "settings": saved})

    @app.route("/api/start", methods=["POST"])
    def api_start():
        data = request.get_json(silent=True) or {}
        tick_s = float(data.get("tick_s", 0.2))
        runtime.start_background(tick_s=tick_s)
        return jsonify({"ok": True, "status": runtime.status()})

    @app.route("/api/stop", methods=["POST"])
    def api_stop():
        runtime.stop_background(join=True)
        return jsonify({"ok": True, "status": runtime.status()})

    @app.route("/api/step", methods=["POST"])
    def api_step():
        return jsonify({"ok": True, "status": runtime.step()})

    @app.route("/api/reset", methods=["POST"])
    def api_reset():
        data = request.get_json(silent=True) or {}
        max_cycles = data.get("max_cycles")
        runtime.stop_background(join=True)
        runtime.reset(max_cycles=max_cycles)
        return jsonify({"ok": True, "status": runtime.status()})

    @atexit.register
    def _shutdown_runtime() -> None:
        closer = getattr(runtime, "close", None)
        if callable(closer):
            closer()
        else:
            runtime.stop_background(join=True)

    return app
