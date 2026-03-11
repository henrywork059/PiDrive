from __future__ import annotations

from .base import BaseAlgorithm


class ManualAlgorithm(BaseAlgorithm):
    name = "manual"
    label = "Manual drive"
    mode = "manual"

    def compute(self, state, camera_service, model_service):
        return float(state.manual_steering), float(state.manual_throttle)
