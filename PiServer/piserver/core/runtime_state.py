from __future__ import annotations

from dataclasses import dataclass, asdict
import time


@dataclass
class RuntimeState:
    manual_steering: float = 0.0
    manual_throttle: float = 0.0
    applied_steering: float = 0.0
    applied_throttle: float = 0.0
    active_algorithm: str = "manual"
    active_model: str = "none"
    recording: bool = False
    safety_stop: bool = False
    max_throttle: float = 0.55
    steer_mix: float = 0.5
    current_page: str = "manual"
    fps: float = 0.0
    camera_backend: str = "unknown"
    camera_width: int = 426
    camera_height: int = 240
    camera_format: str = "BGR888"
    camera_preview_live: bool = False
    camera_error: str = ""
    motor_left: float = 0.0
    motor_right: float = 0.0
    motor_left_direction: int = 1
    motor_right_direction: int = 1
    motor_steering_direction: int = 1
    motor_left_max_speed: float = 1.0
    motor_right_max_speed: float = 1.0
    motor_left_bias: float = 0.0
    motor_right_bias: float = 0.0
    system_message: str = "Ready"
    last_update: float = 0.0

    def snapshot(self) -> dict:
        data = asdict(self)
        data["last_update"] = self.last_update or time.time()
        return data
