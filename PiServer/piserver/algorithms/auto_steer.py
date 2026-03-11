from __future__ import annotations

from .base import BaseAlgorithm


class AutoSteerAlgorithm(BaseAlgorithm):
    name = "auto_steer"
    label = "Lane detection"
    mode = "lane"

    def compute(self, state, frame, model_service, frame_seq: int | None = None):
        uv = model_service.predict_uv_from_frame(frame, frame_seq=frame_seq)
        if uv is None:
            return float(state.manual_steering), float(state.manual_throttle)
        steer, _ = uv
        return float(steer), float(state.manual_throttle)
