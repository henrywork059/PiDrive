from __future__ import annotations

from .base import BaseAlgorithm


class StopAlgorithm(BaseAlgorithm):
    name = "stop"
    label = "Stop / safe idle"
    mode = "stop"

    def compute(self, state, camera_service, model_service):
        return 0.0, 0.0
