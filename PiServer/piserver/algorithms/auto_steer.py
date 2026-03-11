from __future__ import annotations

from .base import BaseAlgorithm


class AutoSteerAlgorithm(BaseAlgorithm):
    name = "auto_steer"
    label = "Auto steer"
    mode = "auto_steer"

    def compute(self, state, camera_service, model_service):
        frame = camera_service.get_latest_frame()
        uv = model_service.predict_uv_from_frame(frame)
        if uv is None:
            return float(state.manual_steering), float(state.manual_throttle)
        steer, _ = uv
        return float(steer), float(state.manual_throttle)
