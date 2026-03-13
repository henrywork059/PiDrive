from __future__ import annotations

from .base import BaseAlgorithm


class AutopilotAlgorithm(BaseAlgorithm):
    name = "autopilot"
    label = "Autopilot"
    mode = "autopilot"

    def compute(self, state, camera_service, model_service):
        frame = camera_service.get_latest_frame(copy=False)
        uv = model_service.predict_uv_from_frame(frame)
        if uv is None:
            return float(state.manual_steering), float(state.manual_throttle)
        steer, throttle = uv
        return float(steer), float(throttle)
