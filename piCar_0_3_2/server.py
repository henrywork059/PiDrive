# server.py
"""
Entry point for Pi-Car web server.

- Creates Flask app
- Creates global Camera instance
- Routes:
    * "/"              -> HTML UI
    * "/video_feed"    -> MJPEG stream
    * "/api/control"   -> control input
    * "/api/record/toggle" -> start/stop recording (currently unused in UI)
    * "/api/status"    -> status bar data
"""

import os
import re
import tempfile
import zipfile

from flask import Flask, Response, render_template_string, request, jsonify, send_file, after_this_request
from model_manager import list_models, save_uploaded_model, load_model, get_model_name

from camera import Camera
from ui_template import INDEX_HTML
from video_stream import mjpeg_generator
from control_api import (
    handle_control_post,
    toggle_recording,
    get_status,
    autopilot_step,
    list_record_sessions,
    get_record_session_path,
    delete_record_session,
)

app = Flask(__name__)

# Tuned for Pi 4: lower resolution but higher FPS for smoother video
camera = Camera(width=426, height=240, fps=30)
camera.start()


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/video_feed")
def video_feed():
    return Response(
        mjpeg_generator(camera),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/control", methods=["POST"])
def api_control():
    data = request.get_json(force=True, silent=True) or {}
    state_copy = handle_control_post(data, camera)
    return jsonify(state_copy)


@app.route("/api/record/toggle", methods=["POST"])
def api_record_toggle():
    recording = toggle_recording()
    return jsonify({"recording": recording})


@app.route("/api/record/list", methods=["GET"])
def api_record_list():
    sessions = list_record_sessions()
    return jsonify({"sessions": sessions})


@app.route("/api/record/download", methods=["GET"])
def api_record_download():
    session = (request.args.get("session", "") or "").strip()

    # Prevent path traversal. Our recorder uses YYYYMMDD-HHMMSS.
    if not re.match(r"^\d{8}-\d{6}$", session):
        return jsonify({"ok": False, "error": "Invalid session name."}), 400

    session_path = get_record_session_path(session)
    if session_path is None:
        return jsonify({"ok": False, "error": "Session not found."}), 404

    # Build zip in a temp file to avoid large in-memory blobs.
    tmp = tempfile.NamedTemporaryFile(prefix=f"picar_rec_{session}_", suffix=".zip", delete=False)
    tmp_path = tmp.name
    tmp.close()

    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in session_path.rglob("*"):
            if not f.is_file():
                continue
            arcname = os.path.join(session, str(f.relative_to(session_path)))
            zf.write(str(f), arcname)

    @after_this_request
    def _cleanup(resp):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return resp

    return send_file(
        tmp_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{session}.zip",
    )


@app.route("/api/record/delete", methods=["POST"])
def api_record_delete():
    data = request.get_json(silent=True) or {}
    session = (data.get("session", "") or "").strip()

    # Prevent path traversal. Our recorder uses YYYYMMDD-HHMMSS.
    if not re.match(r"^\d{8}-\d{6}$", session):
        return jsonify({"ok": False, "error": "Invalid session name."}), 400

    ok, msg = delete_record_session(session)
    if not ok:
        # msg already user-friendly
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True})




@app.route("/api/model/upload", methods=["POST"])
def api_model_upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file part in request."}), 400
    file = request.files["file"]
    ok, msg = save_uploaded_model(file)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "filename": msg})


@app.route("/api/model/list", methods=["GET"])
def api_model_list():
    models = list_models()
    active = get_model_name()
    return jsonify({"models": models, "active": active})


@app.route("/api/model/load", methods=["POST"])
def api_model_load():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "")
    ok, msg = load_model(filename)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "model_name": msg})

@app.route("/api/status", methods=["GET"])
def api_status():
    # Run one background autopilot step (if in auto_steer/autopilot mode)
    autopilot_step(camera)
    return jsonify(get_status())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
