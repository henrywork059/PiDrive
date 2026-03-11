from __future__ import annotations

from .base import BaseAlgorithm


class StopAlgorithm(BaseAlgorithm):
    name = "stop"
    label = "Stop / safe idle"
    mode = "stop"

    def compute(self, state, frame, model_service, frame_seq: int | None = None):
        return 0.0, 0.0
