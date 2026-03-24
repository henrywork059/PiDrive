from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .gui_control_state import GuiControlState

WEB_DIR = Path(__file__).resolve().parent / "gui_web"
APP_VERSION = "0_1_10"


def create_app(mode: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )

    shell = GuiControlState()
    if mode:
        shell.notes.append(f"Launcher requested mode: {mode}")

    app.config["services"] = {"gui_shell": shell}

    @app.route("/")
    def index():
        return render_template("index.html", app_version=APP_VERSION)

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html", app_version=APP_VERSION)

    @app.route("/api/status")
    def api_status():
        return jsonify(shell.snapshot())

    @app.route("/api/page", methods=["POST"])
    def api_page():
        data = request.get_json(silent=True) or {}
        page = shell.set_page(data.get("page"))
        return jsonify({"ok": True, "page": page, "status": shell.snapshot()})

    return app
