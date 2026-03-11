from __future__ import annotations

from .base import BaseAlgorithm


class AutopilotAlgorithm(BaseAlgorithm):
    name = "autopilot"
    label = "Full auto"
    mode = "full_auto"

    def compute(self, state, frame, model_service, frame_seq: int | None = None):
        uv = model_service.predict_uv_from_frame(frame, frame_seq=frame_seq)
        if uv is None:
            return float(state.manual_steering), float(state.manual_throttle)
        steer, throttle = uv
        return float(steer), float(throttle)
