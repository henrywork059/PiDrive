from __future__ import annotations

import atexit
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from .demo_runtime import DemoMissionRuntime, runtime_mode_from_env

WEB_DIR = Path(__file__).resolve().parent / "web"


def _mjpeg(runtime: DemoMissionRuntime):
    while True:
        frame = runtime.latest_frame_jpeg()
        if frame is None:
            runtime.step()
            time.sleep(0.1)
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        time.sleep(0.08)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    runtime = DemoMissionRuntime(max_cycles=2, mode=runtime_mode_from_env("sim"))

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/video_feed")
    def video_feed():
        return Response(_mjpeg(runtime), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/status")
    def api_status():
        return jsonify(runtime.status())

    @app.route("/api/settings")
    def api_settings():
        return jsonify({"ok": True, "settings": runtime.get_settings()})

    @app.route("/api/settings/save", methods=["POST"])
    def api_settings_save():
        data = request.get_json(silent=True) or {}
        settings = data.get("settings") if isinstance(data.get("settings"), dict) else data
        saved = runtime.save_settings(settings)
        if runtime.mode == "live":
            runtime.apply_saved_settings()
        return jsonify({"ok": True, "settings": saved})

    @app.route("/api/start", methods=["POST"])
    def api_start():
        data = request.get_json(silent=True) or {}
        tick_s = float(data.get("tick_s", 0.1 if runtime.mode == "live" else 0.2))
        runtime.start_background(tick_s=tick_s)
        return jsonify({"ok": True, "status": runtime.status()})

    @app.route("/api/stop", methods=["POST"])
    def api_stop():
        runtime.stop_background()
        return jsonify({"ok": True, "status": runtime.status()})

    @app.route("/api/step", methods=["POST"])
    def api_step():
        return jsonify({"ok": True, "status": runtime.step()})

    @app.route("/api/reset", methods=["POST"])
    def api_reset():
        data = request.get_json(silent=True) or {}
        max_cycles = data.get("max_cycles")
        mode = str(data.get("mode", runtime.mode)).strip().lower()
        runtime.stop_background()
        runtime.mode = mode if mode in {"sim", "live"} else runtime.mode
        runtime.reset(max_cycles=max_cycles)
        return jsonify({"ok": True, "status": runtime.status()})

    @atexit.register
    def _shutdown_runtime() -> None:
        runtime.shutdown()

    return app
