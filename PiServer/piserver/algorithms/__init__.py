from .manual import ManualAlgorithm
from .auto_steer import AutoSteerAlgorithm
from .autopilot import AutopilotAlgorithm
from .stop import StopAlgorithm


def build_registry() -> dict:
    algorithms = [
        ManualAlgorithm(),
        AutoSteerAlgorithm(),
        AutopilotAlgorithm(),
        StopAlgorithm(),
    ]
    return {algo.name: algo for algo in algorithms}
