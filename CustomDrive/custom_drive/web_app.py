from __future__ import annotations

import atexit
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .demo_runtime import DemoMissionRuntime

WEB_DIR = Path(__file__).resolve().parent / "web"


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )
    runtime = DemoMissionRuntime(max_cycles=2)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def api_status():
        return jsonify(runtime.status())

    @app.route("/api/start", methods=["POST"])
    def api_start():
        data = request.get_json(silent=True) or {}
        tick_s = float(data.get("tick_s", 0.2))
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
        runtime.stop_background()
        runtime.reset(max_cycles=max_cycles)
        return jsonify({"ok": True, "status": runtime.status()})

    @atexit.register
    def _shutdown_runtime() -> None:
        runtime.stop_background()

    return app
