from __future__ import annotations

from .base import BaseAlgorithm


class AutopilotAlgorithm(BaseAlgorithm):
    name = "autopilot"
    label = "Autopilot"
    mode = "autopilot"

    def compute(self, state, camera_service, model_service):
        frame = camera_service.get_latest_frame(copy=False)
        return self.compute_from_frame(state, frame, model_service)

    def compute_from_frame(self, state, frame, model_service):
        uv = model_service.predict_uv_from_frame(frame)
        if uv is None:
            return float(state.manual_steering), float(state.manual_throttle)
        steer, throttle = uv
        return float(steer), float(throttle)
