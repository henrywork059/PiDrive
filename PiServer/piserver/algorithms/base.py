from __future__ import annotations


class BaseAlgorithm:
    name = "base"
    label = "Base"
    mode = "manual"

    def compute(self, state, frame, model_service, frame_seq: int | None = None):
        return 0.0, 0.0
