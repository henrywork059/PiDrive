from __future__ import annotations


class BaseAlgorithm:
    name = "base"
    label = "Base"
    mode = "manual"

    def compute(self, state, camera_service, model_service):
        return 0.0, 0.0
