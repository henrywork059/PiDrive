# control_api.py
"""Implements control and recording logic used by Flask routes."""

import time
import threading
import shutil

from motor_controller import MotorController
from data_recorder import DataRecorder
from pathlib import Path
from video_stream import get_fps
from model_manager import get_model_name
from autopilot import predict_uv_from_camera
from recorder_step import record_step
from control_state import make_initial_state

MODEL_NAME = "demo_model"

control_state = make_initial_state()
control_lock = threading.Lock()

motor = MotorController()
recorder = DataRecorder()


def handle_control_post(data: dict, camera):
    with control_lock:
        if "steering" in data:
            control_state["steering"] = float(data["steering"])
        if "throttle" in data:
            control_state["throttle"] = float(data["throttle"])
        if "mode" in data:
            mode = str(data["mode"])
            if mode in ("manual", "auto_steer", "autopilot"):
                control_state["mode"] = mode

        control_state["last_update"] = time.time()

        motor.update(
            steering=control_state["steering"],
            throttle=control_state["throttle"],
            mode=control_state["mode"],
        )

        record_step(recorder, camera, control_state)

        return dict(control_state)


def autopilot_step(camera):
    """Background step called from /api/status to run the model in auto modes.

    - In manual mode: does nothing.
    - In auto_steer: model controls steering only; throttle remains user-set.
    - In autopilot: model controls both steering and throttle.
    """
    with control_lock:
        mode = control_state.get("mode", "manual")
        if mode not in ("auto_steer", "autopilot"):
            return

        # Ask the TFLite model (if any) for predicted (u, v) = (steering, throttle)
        uv = predict_uv_from_camera(camera)
        if uv is None:
            return

        u, v = uv

        steering = float(u)
        if mode == "auto_steer":
            throttle = float(control_state.get("throttle", 0.0))
        else:  # autopilot
            throttle = float(v)

        # Safety clamp
        steering = max(-1.0, min(1.0, steering))
        throttle = max(0.0, min(1.0, throttle))

        control_state["steering"] = steering
        control_state["throttle"] = throttle
        control_state["last_update"] = time.time()

        motor.update(
            steering=control_state["steering"],
            throttle=control_state["throttle"],
            mode=control_state["mode"],
        )

        # Record what actually got sent to the motors
        record_step(recorder, camera, control_state)



def toggle_recording() -> bool:
    with control_lock:
        recorder.toggle()
        return recorder.recording


def get_status() -> dict:
    with control_lock:
        # NOTE: `speed` is kept as a backward-compat alias of `throttle`.
        # The UI (0_2_10+) uses `throttle`.
        thr = float(control_state["throttle"])
        return {
            "mode": control_state["mode"],
            "steering": float(control_state["steering"]),
            "throttle": thr,
            "speed": thr,
            "recording": recorder.recording,
            "model_name": get_model_name(),
            "fps": float(get_fps()),
            "last_update": control_state["last_update"],
        }


def list_record_sessions() -> list[str]:
    """Return all known recording session folder names (newest first)."""
    root: Path = recorder.root
    if not root.exists():
        return []
    sessions = [p.name for p in root.iterdir() if p.is_dir()]
    sessions.sort(reverse=True)
    return sessions


def get_record_session_path(name: str) -> Path | None:
    """Return absolute path to a session folder if it exists."""
    p = recorder.root / name
    return p if p.is_dir() else None


def get_active_record_session_name() -> str | None:
    """Return the active recording session name, if currently recording."""
    with control_lock:
        if not recorder.recording or recorder.session_path is None:
            return None
        return recorder.session_path.name


def delete_record_session(name: str) -> tuple[bool, str]:
    """Delete a recording session folder.

    Returns (ok, message).
    - Refuses to delete the currently-active session while recording.
    """
    with control_lock:
        if recorder.recording and recorder.session_path is not None and recorder.session_path.name == name:
            return False, "Cannot delete an active recording session. Stop recording first."

        p = recorder.root / name
        if not p.is_dir():
            return False, "Session not found."

        try:
            shutil.rmtree(p)
        except Exception as e:
            return False, f"Failed to delete session: {e}"

        return True, "Deleted."
