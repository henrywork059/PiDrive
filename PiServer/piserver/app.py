from __future__ import annotations

from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from piserver.algorithms import build_registry
from piserver.core.config_store import ConfigStore
from piserver.services import (
    CameraService,
    ControlService,
    ModelService,
    MotorService,
    RecorderService,
    UpdateService,
)


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent / "web"


def mjpeg_generator(camera_service):
    while True:
        frame = camera_service.get_jpeg_frame()
        if frame is None:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )

    camera_service = CameraService()
    camera_service.start()

    motor_service = MotorService()
    model_service = ModelService(BASE_DIR / "models")
    recorder_service = RecorderService(BASE_DIR / "data" / "records")
    config_store = ConfigStore(BASE_DIR / "config" / "runtime.json")
    algorithms = build_registry()
    control_service = ControlService(
        camera_service=camera_service,
        motor_service=motor_service,
        model_service=model_service,
        recorder_service=recorder_service,
        algorithms=algorithms,
        config_store=config_store,
        loop_hz=20,
    )
    control_service.start()

    update_service = UpdateService(BASE_DIR)

    app.config["services"] = {
        "camera": camera_service,
        "motor": motor_service,
        "model": model_service,
        "recorder": recorder_service,
        "control": control_service,
        "update": update_service,
        "algorithms": algorithms,
    }

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/video_feed")
    def video_feed():
        return Response(
            mjpeg_generator(camera_service),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/api/status")
    def api_status():
        snap = control_service.snapshot()
        git = update_service.git_status()
        snap["git"] = git
        snap["restart"] = update_service.restart_status()
        return jsonify(snap)

    @app.route("/api/system/repo_status")
    def api_system_repo_status():
        force = request.args.get("force", "0") in {"1", "true", "yes"}
        return jsonify(update_service.git_status(force=force))

    @app.route("/api/algorithms")
    def api_algorithms():
        payload = []
        for algo in algorithms.values():
            payload.append(
                {"name": algo.name, "label": algo.label, "mode": getattr(algo, "mode", algo.name)}
            )
        return jsonify({"algorithms": payload})

    @app.route("/api/control", methods=["POST"])
    def api_control():
        data = request.get_json(silent=True) or {}
        control_service.set_manual_controls(
            steering=data.get("steering"),
            throttle=data.get("throttle"),
        )
        control_service.set_runtime_parameters(
            max_throttle=data.get("max_throttle"),
            steer_mix=data.get("steer_mix"),
            current_page=data.get("current_page"),
        )
        if "algorithm" in data:
            control_service.select_algorithm(data.get("algorithm"))
        return jsonify(control_service.snapshot())

    @app.route("/api/algorithm/select", methods=["POST"])
    def api_algorithm_select():
        data = request.get_json(silent=True) or {}
        ok, msg = control_service.select_algorithm(data.get("name"))
        code = 200 if ok else 400
        return jsonify({"ok": ok, "message": msg, "state": control_service.snapshot()}), code

    @app.route("/api/record/toggle", methods=["POST"])
    def api_record_toggle():
        return jsonify({"recording": control_service.toggle_recording()})

    @app.route("/api/model/list")
    def api_model_list():
        return jsonify(
            {
                "models": model_service.list_models(),
                "active": model_service.get_active_name(),
            }
        )

    @app.route("/api/model/upload", methods=["POST"])
    def api_model_upload():
        file = request.files.get("file")
        if file is None:
            return jsonify({"ok": False, "error": "No file uploaded."}), 400
        ok, msg = model_service.save_uploaded_model(file)
        code = 200 if ok else 400
        return jsonify({"ok": ok, "message": msg, "active": model_service.get_active_name()}), code

    @app.route("/api/model/load", methods=["POST"])
    def api_model_load():
        data = request.get_json(silent=True) or {}
        ok, msg = model_service.load_model(data.get("filename", ""))
        code = 200 if ok else 400
        return jsonify({"ok": ok, "message": msg, "active": model_service.get_active_name()}), code

    @app.route("/api/config/save", methods=["POST"])
    def api_config_save():
        return jsonify({"ok": True, "config": control_service.save_runtime_config()})

    @app.route("/api/config/reload", methods=["POST"])
    def api_config_reload():
        return jsonify({"ok": True, "config": control_service.reload_runtime_config()})

    @app.route("/api/system/estop", methods=["POST"])
    def api_estop():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get("enabled", True))
        control_service.set_safety_stop(enabled)
        if enabled:
            motor_service.stop()
        return jsonify({"ok": True, "state": control_service.snapshot()})

    @app.route("/api/system/update", methods=["POST"])
    def api_system_update():
        allowed, reason = control_service.can_run_system_action()
        if not allowed:
            return jsonify({"ok": False, "message": reason}), 400
        ok, text = update_service.git_pull()
        return jsonify({"ok": ok, "message": text})

    @app.route("/api/system/restart", methods=["POST"])
    def api_system_restart():
        allowed, reason = control_service.can_run_system_action()
        if not allowed:
            return jsonify({"ok": False, "message": reason}), 400
        ok, text = update_service.restart_service()
        return jsonify({"ok": ok, "message": text})

    return app
