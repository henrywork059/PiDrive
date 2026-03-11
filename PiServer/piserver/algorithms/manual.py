from __future__ import annotations

from .base import BaseAlgorithm


class ManualAlgorithm(BaseAlgorithm):
    name = "manual"
    label = "Manual drive"
    mode = "manual"

    def compute(self, state, frame, model_service, frame_seq: int | None = None):
        return float(state.manual_steering), float(state.manual_throttle)
