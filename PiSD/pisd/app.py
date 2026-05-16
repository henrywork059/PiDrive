from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pisd import __version__
from pisd.core.errors import ErrorReporter, PiSDErrorCodes, ok_payload, report_payload
from pisd.core.panel_contracts import build_panel_testing_manifest, get_panel_contracts
from pisd.services.camera_service import CameraService
from pisd.services.motor_service import MotorService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = PROJECT_ROOT / "config" / "defaults.json"
APP_ERRORS = ErrorReporter("app")
WEB_ROOT = Path(__file__).resolve().parent / "web"
WEB_TEMPLATE_DIR = WEB_ROOT / "templates"
WEB_STATIC_DIR = WEB_ROOT / "static"


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
        from flask import Flask, Response, jsonify, render_template, request
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

    app = Flask(
        __name__,
        template_folder=str(WEB_TEMPLATE_DIR),
        static_folder=str(WEB_STATIC_DIR),
        static_url_path="/testing/static",
    )
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

    def test_gui_manifest() -> dict[str, Any]:
        return {
            "app": "PiSD",
            "version": __version__,
            "code": PiSDErrorCodes.OK,
            "message": "Testing server GUI endpoint manifest loaded.",
            "pages": ["/", "/manual-drive", "/settings", "/dashboard", "/testing", "/panel-presentation", "/panel-testing"],
            "front_page": {"path": "/", "purpose": "Mode selection landing page."},
            "manual_drive": {"path": "/manual-drive", "purpose": "Simple user driving page with camera preview, status, STOP, and manual pad."},
            "settings_tab": {"path": "/settings", "purpose": "Settings tab for camera/motor/system API checks."},
            "main_dashboard": {"path": "/dashboard", "purpose": "Actual GUI dashboard shell v1."},
            "panel_presentation": {"path": "/panel-presentation", "purpose": "Browser-local panel presentation settings that apply across pages."},
            "static_base": "/testing/static/",
            "endpoints": [
                {"method": "GET", "path": "/api/status", "purpose": "Read full PiSD camera/motor/error status."},
                {"method": "GET", "path": "/api/errors", "purpose": "Read recent app, camera, and motor error history."},
                {"method": "POST", "path": "/api/errors/clear", "purpose": "Clear error history."},
                {"method": "POST", "path": "/api/camera/start", "purpose": "Start camera service."},
                {"method": "POST", "path": "/api/camera/stop", "purpose": "Stop camera service."},
                {"method": "GET", "path": "/api/camera/config", "purpose": "Read current camera settings."},
                {"method": "GET", "path": "/api/camera/capabilities", "purpose": "Read Picamera2 capabilities when available."},
                {"method": "POST", "path": "/api/camera/apply", "purpose": "Apply camera settings and restart camera."},
                {"method": "GET", "path": "/api/camera/frame.jpg", "purpose": "Fetch one cached JPEG frame/snapshot."},
                {"method": "GET", "path": "/video_feed", "purpose": "Multipart MJPEG live preview feed using frame notifications."},
                {"method": "GET", "path": "/api/camera/fps-stats", "purpose": "Read measured camera capture, encode, and frame-byte statistics."},
                {"method": "GET", "path": "/api/motor/config", "purpose": "Read current motor settings."},
                {"method": "POST", "path": "/api/motor/apply", "purpose": "Apply motor settings without moving the car."},
                {"method": "POST", "path": "/api/motor/test-channel", "purpose": "Test one motor side/direction/speed/duration."},
                {"method": "POST", "path": "/api/control/manual", "purpose": "Send manual steering/throttle command."},
                {"method": "POST", "path": "/api/control/stop", "purpose": "Emergency stop / set outputs to zero."},
            ],
            "known_good_camera": {
                "visual_reference": "01_request_awb_auto",
                "array_reference": "91_array_rgb_confirmed_correct",
                "capture_source": "request",
                "array_color_order": "rgb",
                "live_preview_endpoint": "/video_feed",
                "fps_stats_endpoint": "/api/camera/fps-stats",
                "fast_preview_preset": {
                    "capture_source": "array",
                    "array_color_order": "rgb",
                    "width": 426,
                    "height": 240,
                    "fps": 30,
                    "preview_quality": 50,
                    "buffer_count": 4,
                    "queue": True,
                },
            },
            "safety": {
                "motor_output_default": "locked",
                "real_motor_channel_tests_require_enable_motor_output": True,
                "keep_wheels_lifted": True,
            },
        }


    def panel_testing_manifest() -> dict[str, Any]:
        return build_panel_testing_manifest(__version__)

    def panel_contracts_payload() -> dict[str, Any]:
        return ok_payload(
            "Panel API contracts loaded.",
            panels=get_panel_contracts(),
            contract_failure_code=PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
            future_placeholder_code=PiSDErrorCodes.TEST_PANEL_CONTRACT_SKIPPED,
        )

    @app.get("/")
    def front_page():
        return render_template(
            "front_page.html",
            initial_status=build_status(),
            manifest=test_gui_manifest(),
        )

    @app.get("/manual-drive")
    def manual_drive():
        return render_template(
            "manual_drive.html",
            initial_status=build_status(),
        )

    @app.get("/settings")
    def settings_tab():
        return render_template(
            "settings_tab.html",
            initial_status=build_status(),
        )

    @app.get("/dashboard")
    def main_dashboard():
        return render_template(
            "main_dashboard.html",
            initial_status=build_status(),
        )

    @app.get("/testing")
    def index():
        return render_template(
            "testing_server.html",
            initial_status=build_status(),
            manifest=test_gui_manifest(),
        )

    @app.get("/api/test-gui/manifest")
    def api_test_gui_manifest():
        return jsonify(test_gui_manifest())

    @app.get("/panel-presentation")
    def panel_presentation():
        return render_template(
            "panel_presentation.html",
            initial_status=build_status(),
        )

    @app.get("/panel-testing")
    def panel_testing():
        return render_template(
            "panel_testing.html",
            initial_status=build_status(),
            panel_manifest=panel_testing_manifest(),
        )

    @app.get("/api/panel-presentation/manifest")
    def api_panel_presentation_manifest():
        return jsonify(ok_payload(
            "Panel presentation settings manifest loaded.",
            storage_key="pisd.panelPresentation.v1",
            path="/panel-presentation",
            applies_to=["/", "/manual-drive", "/settings", "/testing", "/dashboard", "/panel-testing", "/panel-presentation"],
            controls=[
                "theme",
                "layoutMode",
                "density",
                "fontScale",
                "panelGap",
                "panelRadius",
                "borderStrength",
                "shadowStrength",
                "minPanelWidth",
                "previewAspect",
                "previewFit",
                "panelPadding",
                "panelHeaderMode",
                "buttonScale",
                "consoleHeight",
                "cardAccent",
                "autoSave",
            ],
        ))

    @app.get("/api/panel-testing/manifest")
    def api_panel_testing_manifest():
        return jsonify(panel_testing_manifest())

    @app.get("/api/panel-testing/contracts")
    def api_panel_testing_contracts():
        return jsonify(panel_contracts_payload())

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

    @app.get("/api/camera/capabilities")
    def api_camera_capabilities():
        try:
            return jsonify(ok_payload("Camera capabilities loaded.", capabilities=camera_service.get_capabilities()))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera capabilities API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

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
            frame, _seq, _timestamp, _bytes = camera_service.get_jpeg_frame_info()
            if frame is None:
                camera_service.start()
                frame, _seq, _timestamp, _bytes = camera_service.wait_for_jpeg_frame(timeout=1.0)
            if frame is None:
                report = camera_service._record(  # internal service helper used to keep status and API code aligned
                    PiSDErrorCodes.CAMERA_NO_FRAME,
                    "No JPEG camera frame is available yet.",
                    context={"path": request.path},
                )
                return jsonify(report_payload(False, report)), 503
            return Response(
                frame,
                mimetype="image/jpeg",
                headers={
                    "Cache-Control": "no-store, max-age=0",
                    "X-PiSD-Frame-Seq": str(_seq),
                    "X-PiSD-Frame-At": str(_timestamp),
                    "X-PiSD-Frame-Bytes": str(_bytes),
                },
            )
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera frame API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.get("/api/camera/fps-stats")
    def api_camera_fps_stats():
        try:
            return jsonify(ok_payload("Camera FPS statistics loaded.", stats=camera_service.get_fps_stats(), camera=camera_service.get_config()))
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Camera FPS stats API failed: {exc}", exc=exc)
            return jsonify(report_payload(False, report)), 500

    @app.get("/video_feed")
    def video_feed():
        def generate():
            camera_service.start()
            last_seq = None
            while True:
                frame, seq, _timestamp, _bytes = camera_service.wait_for_jpeg_frame(last_seq=last_seq, timeout=2.0)
                if frame is None:
                    continue
                if last_seq is not None and seq == last_seq:
                    continue
                last_seq = seq
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"X-PiSD-Frame-Seq: {seq}\r\n".encode("ascii")
                    + f"X-PiSD-Frame-Bytes: {_bytes}\r\n\r\n".encode("ascii")
                    + frame
                    + b"\r\n"
                )

        return Response(
            generate(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

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

    @app.post("/api/motor/test-channel")
    def api_motor_test_channel():
        data, json_error = get_json_payload()
        if json_error is not None:
            return jsonify(report_payload(False, json_error)), 400
        try:
            if motor_service.hardware_enabled and not bool(data.get("enable_motor_output", False)):
                report = motor_service.errors.report(
                    PiSDErrorCodes.MOTOR_TEST_UNARMED,
                    "Motor channel test refused because enable_motor_output was not true.",
                    context={"path": request.path},
                )
                return jsonify(report_payload(False, report, motor=motor_service.status())), 403
            result = motor_service.test_motor_channel(
                side=data.get("side", ""),
                direction=data.get("direction", 1),
                speed=data.get("speed", 0.2),
                duration=data.get("duration", 0.35),
                apply_config_direction=bool(data.get("apply_config_direction", False)),
            )
            status_code = 200 if result.get("ok") else 400
            return jsonify(result), status_code
        except Exception as exc:
            report = APP_ERRORS.report(PiSDErrorCodes.API_SERVICE_EXCEPTION, f"Motor channel test API failed: {exc}", exc=exc)
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
