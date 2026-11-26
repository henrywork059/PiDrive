from __future__ import annotations

import atexit
import tempfile
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

from piserver.algorithms import build_registry
from piserver.core.config_store import ConfigStore
from piserver.core.access_control import install_access_control
from piserver.core.request_trace import install_mutation_trace
from piserver.core.preflight import build_preflight
from piserver.core.recent_events import RecentEventRing, record_api_response
from piserver.services.camera_service import CameraService
from piserver.services.control_service import ControlService
from piserver.services.model_service import ModelService
from piserver.services.motor_service import MotorService
from piserver.services.recorder_service import RecorderService

BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent / "web"
APP_VERSION = "0_4_46"


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
    install_access_control(app)
    install_mutation_trace(app)
    recent_events = RecentEventRing(capacity=128)
    event_routes = {
        "api_camera_preview_state": "camera_preview",
        "api_camera_apply": "camera_apply",
        "api_motor_apply": "motor_apply",
        "api_model_upload": "model_upload",
        "api_model_load": "model_load",
        "api_model_delete": "model_delete",
        "api_record_toggle": "record_toggle",
        "api_record_capture_once": "record_capture",
        "api_record_delete": "record_delete",
        "api_config_save": "config_save",
        "api_config_reload": "config_reload",
        "api_estop": "safety_stop",
        "api_safety_rearm": "safety_rearm",
    }

    @app.after_request
    def record_operator_event(response):
        return record_api_response(recent_events, response, request, event_routes)


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
    recent_events.record("startup", "observed")

    def cleanup_services():
        try:
            control_service.stop()
        except Exception:
            pass
        try:
            camera_service.stop()
        except Exception:
            pass
        try:
            motor_service.close()
        except Exception:
            pass

    atexit.register(cleanup_services)

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
        # Read bytes and publication sequence atomically; never reset freshness
        # merely because a cached JPEG can still be returned by the service.
        frame, sequence = camera_service.wait_for_jpeg(-1, timeout=0.0)
        if frame is None:
            camera_service.wait_for_jpeg(0, timeout=0.35)
            frame, sequence = camera_service.wait_for_jpeg(-1, timeout=0.0)
        if frame is None:
            return ("", 204)
        response = Response(frame, mimetype="image/jpeg")
        response.headers["X-Preview-Seq"] = str(sequence)
        response.headers["X-Preview-Live"] = "1" if camera_service.get_config().get("preview_live") else "0"
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
        state = control_service.snapshot()
        state['performance_diagnostics'] = {
            'controller': state.get('performance'),
            'camera': camera_service.get_performance() if hasattr(camera_service, 'get_performance') else None,
            'model': model_service.get_performance() if hasattr(model_service, 'get_performance') else None,
            'camera_frame_age_s': camera_service.get_raw_frame_age(),
        }
        state["server_status_at_ms"] = int(time.time() * 1000)
        state["config_recovery"] = getattr(config_store, "recovery_status", lambda: {})()
        return jsonify(state)

    @app.get("/api/preflight")
    def api_preflight():
        # R48: inspect already initialized services; no motor/camera/AI action.
        active_name = model_service.get_active_name()
        return jsonify(build_preflight(
            camera=camera_service.get_config(),
            motor=motor_service.get_config(),
            model_active=bool(active_name and str(active_name).lower() != "none"),
            safety=control_service.safety_status(),
            disk_root=BASE_DIR,
        ))

    @app.get("/api/recent-events")
    def api_recent_events():
        return jsonify({"ok": True, "capacity": recent_events.capacity, "events": recent_events.snapshot()})

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
        data = request.get_json(silent=True)
        ok, message = control_service.apply_control_update(data)
        if not ok:
            return jsonify({"ok": False, "message": message, "state": control_service.snapshot()}), 400
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

    @app.route("/api/record/capture_once", methods=["POST"])
    def api_record_capture_once():
        frame = camera_service.capture_snapshot_frame(retries=7, delay_s=0.05, copy=True)
        ok, message = recorder_service.capture_once(frame, control_service.snapshot())
        code = 200 if ok else 503
        return jsonify({"ok": ok, "message": message, "state": control_service.snapshot()}), code

    @app.route("/api/record/sessions")
    def api_record_sessions():
        return jsonify({"ok": True, "sessions": recorder_service.list_sessions()})

    @app.route("/api/record/download")
    def api_record_download():
        session_name = str(request.args.get("session", "")).strip()
        if not session_name:
            return jsonify({"ok": False, "message": "Choose a session first."}), 400
        temp_file = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        ok, payload = recorder_service.write_session_zip(session_name, temp_file)
        if not ok:
            temp_file.close()
            return jsonify({"ok": False, "message": payload}), 404
        temp_file.seek(0)
        return send_file(
            temp_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{payload}.zip",
            max_age=0,
        )

    @app.route("/api/record/delete", methods=["POST"])
    def api_record_delete():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "message": "Expected a JSON object."}), 400
        session_name = str(data.get("session", "")).strip()
        if not session_name:
            return jsonify({"ok": False, "message": "Choose a session folder first."}), 400
        if data.get("confirm") is not True:
            return jsonify({"ok": False, "message": "Explicit deletion confirmation required. No recording files were removed."}), 400
        ok, message = recorder_service.delete_folder(session_name)
        code = 200 if ok else 409
        return jsonify({"ok": ok, "message": message, "sessions": recorder_service.list_sessions(), "state": control_service.snapshot()}), code

    @app.route("/api/model/list")
    def api_model_list():
        return jsonify({"models": model_service.list_models(), "active": model_service.get_active_name(), "input_spec": model_service.get_input_spec(), "model_metadata": model_service.get_model_metadata()})

    @app.route("/api/model/upload", methods=["POST"])
    def api_model_upload():
        file = request.files.get("file")
        if file is None:
            return jsonify({"ok": False, "error": "No file uploaded."}), 400
        ok, msg = model_service.save_uploaded_model(file, request.files.get("manifest"))
        code = 200 if ok else 400
        return jsonify({"ok": ok, "message": msg, "active": model_service.get_active_name()}), code

    @app.route("/api/model/load", methods=["POST"])
    def api_model_load():
        data = request.get_json(silent=True) or {}
        ok, msg = model_service.load_model(data.get("filename", ""))
        code = 200 if ok else 400
        return jsonify({"ok": ok, "message": msg, "active": model_service.get_active_name(), "input_spec": model_service.get_input_spec(), "model_metadata": model_service.get_model_metadata()}), code

    @app.route("/api/model/delete", methods=["POST"])
    def api_model_delete():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or data.get("confirm") is not True:
            return jsonify({"ok": False, "message": "Explicit model deletion confirmation required; no model files were removed."}), 400
        filename = data.get("filename", "")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename or "\\" in filename:
            return jsonify({"ok": False, "message": "Choose an exact listed model filename."}), 400
        ok, msg = model_service.delete_model(filename)
        code = 200 if ok else 404
        return jsonify({"ok": ok, "message": msg, "models": model_service.list_models(), "active": model_service.get_active_name()}), code

    @app.route("/api/config/save", methods=["POST"])
    def api_config_save():
        try:
            config = control_service.save_runtime_config()
        except (OSError, ValueError, TypeError):
            return jsonify({"ok": False, "saved": False, "message": "Config not saved. Original file retained; check recovery status.",
                            "config_recovery": getattr(config_store, "recovery_status", lambda: {})()}), 500
        return jsonify({"ok": True, "config": config, "message": "Config saved.",
                        "config_recovery": getattr(config_store, "recovery_status", lambda: {})()})

    @app.route("/api/config/reload", methods=["POST"])
    def api_config_reload():
        try:
            config = control_service.reload_runtime_config()
        except (OSError, ValueError):
            return jsonify({"ok": False, "message": "Config reload refused. Current settings retained; check recovery status.",
                            "config_recovery": getattr(config_store, "recovery_status", lambda: {})()}), 409
        return jsonify({"ok": True, "config": config, "message": "Config reloaded.",
                        "config_recovery": getattr(config_store, "recovery_status", lambda: {})()})

    @app.route("/api/safety/status")
    def api_safety_status():
        return jsonify({"ok": True, "safety": control_service.safety_status()})

    @app.route("/api/safety/rearm", methods=["POST"])
    def api_safety_rearm():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "message": "Expected a JSON object.", "safety": control_service.safety_status()}), 400
        ok, message = control_service.rearm_safety(confirm=data.get("confirm"))
        return jsonify({"ok": ok, "message": message, "safety": control_service.safety_status(),
                        "state": control_service.snapshot()}), 200 if ok else 409

    @app.route("/api/system/estop", methods=["POST"])
    def api_estop():
        # STOP must remain usable with an empty or malformed body; never allow
        # invalid input to be interpreted as a request to clear the latch.
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        if type(data.get("enabled", True)) is not bool:
            return jsonify({"ok": False, "message": "enabled must be a JSON boolean."}), 400
        if data.get("enabled", True):
            control_service.set_safety_stop(True)
            motor_service.stop()
            ok, message = True, "Emergency stop engaged."
        else:
            # Legacy toggle remains supported, but may not bypass explicit rearm.
            ok, message = control_service.rearm_safety(confirm=data.get("confirm"))
        return jsonify({"ok": ok, "message": message, "safety": control_service.safety_status(),
                        "state": control_service.snapshot()}), 200 if ok else 409

    @app.route("/api/motor/config")
    def api_motor_config():
        return jsonify({"ok": True, "config": motor_service.get_config()})

    @app.route("/api/motor/apply", methods=["POST"])
    def api_motor_apply():
        data = request.get_json(silent=True) or {}
        try:
            config = motor_service.apply_settings(data)
            control_service.invalidate_processing_state_cache()
        except Exception as exc:
            return jsonify({"ok": False, "message": f"Motor settings failed: {exc}"}), 400
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
        control_service.invalidate_processing_state_cache()
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
