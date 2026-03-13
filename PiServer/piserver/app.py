from __future__ import annotations

from pathlib import Path
import time

from flask import Flask, Response, jsonify, render_template, request

from piserver.algorithms import build_registry
from piserver.core.config_store import ConfigStore
from piserver.services.camera_service import CameraService
from piserver.services.control_service import ControlService
from piserver.services.model_service import ModelService
from piserver.services.motor_service import MotorService
from piserver.services.recorder_service import RecorderService


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent / "web"
APP_VERSION = "0_2_1"


def mjpeg_generator(camera_service):
    seq = 0
    while True:
        frame, seq = camera_service.wait_for_jpeg(seq, timeout=1.0)
        if frame is None:
            time.sleep(0.05)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-store, no-cache, must-revalidate, max-age=0\r\n"
            b"Pragma: no-cache\r\n\r\n" + frame + b"\r\n"
        )


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / "templates"),
        static_folder=str(WEB_DIR / "static"),
    )

    config_store = ConfigStore(BASE_DIR / "config" / "runtime.json")
    initial_config = config_store.load()

    camera_service = CameraService()
    if isinstance(initial_config.get("camera"), dict):
        camera_service.apply_settings(initial_config.get("camera"), restart=False)
    camera_service.start()

    motor_service = MotorService()
    model_service = ModelService(BASE_DIR / "models")
    recorder_service = RecorderService(BASE_DIR / "data" / "records")
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

    app.config["services"] = {
        "camera": camera_service,
        "motor": motor_service,
        "model": model_service,
        "recorder": recorder_service,
        "control": control_service,
        "algorithms": algorithms,
    }

    @app.route("/")
    def index():
        return render_template("index.html", app_version=APP_VERSION)

    @app.route("/video_feed")
    def video_feed():
        response = Response(
            mjpeg_generator(camera_service),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


    @app.route("/api/camera/frame.jpg")
    def api_camera_frame():
        frame = camera_service.get_jpeg_frame()
        if frame is None:
            frame, _ = camera_service.wait_for_jpeg(0, timeout=0.35)
        if frame is None:
            return ("", 204)
        response = Response(frame, mimetype="image/jpeg")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/api/camera/preview_state", methods=["POST"])
    def api_camera_preview_state():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get("enabled", True))
        camera_service.set_preview_enabled(enabled)
        return jsonify({"ok": True, "config": camera_service.get_config(), "enabled": enabled})

    @app.route("/api/status")
    def api_status():
        return jsonify(control_service.snapshot())

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
        ok_controls, msg_controls = control_service.set_manual_controls(
            steering=data.get("steering"),
            throttle=data.get("throttle"),
        )
        ok_runtime, msg_runtime = control_service.set_runtime_parameters(
            max_throttle=data.get("max_throttle"),
            steer_mix=data.get("steer_mix"),
            current_page=data.get("current_page"),
        )
        if "algorithm" in data:
            ok_algo, msg_algo = control_service.select_algorithm(data.get("algorithm"))
            if not ok_algo:
                return jsonify({"ok": False, "message": msg_algo, "state": control_service.snapshot()}), 400
        if not ok_controls:
            return jsonify({"ok": False, "message": msg_controls, "state": control_service.snapshot()}), 400
        if not ok_runtime:
            return jsonify({"ok": False, "message": msg_runtime, "state": control_service.snapshot()}), 400
        return jsonify(control_service.snapshot())

    @app.route("/api/algorithm/select", methods=["POST"])
    def api_algorithm_select():
        data = request.get_json(silent=True) or {}
        ok, msg = control_service.select_algorithm(data.get("name"))
        code = 200 if ok else 400
        return jsonify({"ok": ok, "message": msg, "state": control_service.snapshot()}), code

    @app.route("/api/record/toggle", methods=["POST"])
    def api_record_toggle():
        ok, recording, message = control_service.toggle_recording()
        code = 200 if ok else 423
        return jsonify({"ok": ok, "recording": recording, "message": message, "state": control_service.snapshot()}), code

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
        config = control_service.save_runtime_config()
        return jsonify({"ok": True, "config": config, "message": "Config saved."})

    @app.route("/api/config/reload", methods=["POST"])
    def api_config_reload():
        config = control_service.reload_runtime_config()
        return jsonify({"ok": True, "config": config, "message": "Config reloaded."})

    @app.route("/api/system/estop", methods=["POST"])
    def api_estop():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get("enabled", True))
        control_service.set_safety_stop(enabled)
        if enabled:
            motor_service.stop()
        return jsonify({"ok": True, "state": control_service.snapshot()})



    @app.route("/api/motor/config")
    def api_motor_config():
        return jsonify({"ok": True, "config": motor_service.get_config()})

    @app.route("/api/motor/apply", methods=["POST"])
    def api_motor_apply():
        data = request.get_json(silent=True) or {}
        config = motor_service.apply_settings(data)
        saved = False
        save_error = ""
        try:
            config_store.save(control_service.get_runtime_config())
            saved = True
        except Exception as exc:
            save_error = str(exc)
        message = "Motor settings applied. Motors stopped for safety."
        if saved:
            message += " Settings saved."
        elif save_error:
            message += f" Settings were not saved: {save_error}"
        return jsonify({
            "ok": True,
            "saved": saved,
            "message": message,
            "config": config,
            "state": control_service.snapshot(),
        })

    @app.route("/api/camera/config")
    def api_camera_config():
        return jsonify({"ok": True, "config": camera_service.get_config()})

    @app.route("/api/camera/apply", methods=["POST"])
    def api_camera_apply():
        data = request.get_json(silent=True) or {}
        ok, message, config = camera_service.apply_settings(data, restart=True)
        saved = False
        save_error = ""
        try:
            config_store.save(control_service.get_runtime_config())
            saved = True
        except Exception as exc:
            save_error = str(exc)
        if saved:
            message = f"{message} Settings saved."
        elif save_error:
            message = f"{message} Settings were not saved: {save_error}"
        code = 200 if ok else 400
        return jsonify({
            "ok": ok,
            "saved": saved,
            "message": message,
            "config": config,
            "state": control_service.snapshot(),
        }), code

    return app
