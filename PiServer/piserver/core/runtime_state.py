from __future__ import annotations

from dataclasses import dataclass, asdict, field
import time


def default_mode_profiles() -> dict:
    return {
        "manual": {"max_throttle": 0.55, "steer_mix": 0.50},
        "lane": {"max_throttle": 0.40, "steer_mix": 0.58},
        "full_auto": {"max_throttle": 0.45, "steer_mix": 0.55},
    }


def default_calibration() -> dict:
    return {
        "left_motor_scale": 1.00,
        "right_motor_scale": 1.00,
        "global_speed_limit": 0.75,
        "turn_gain": 1.00,
        "camera_width": 426,
        "camera_height": 240,
        "camera_fps": 30,
        "camera_format": "BGR888",
        "auto_exposure": True,
        "exposure_time": 12000,
        "analogue_gain": 1.5,
        "exposure_compensation": 0.0,
        "auto_white_balance": True,
        "brightness": 0.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "sharpness": 1.0,
    }


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
    drive_mode: str = "manual"
    current_page: str = "manual"
    max_throttle: float = 0.55
    steer_mix: float = 0.5
    mode_profiles: dict = field(default_factory=default_mode_profiles)
    calibration: dict = field(default_factory=default_calibration)
    fps: float = 0.0
    camera_backend: str = "unknown"
    camera_width: int = 426
    camera_height: int = 240
    camera_format: str = "BGR888"
    motor_left: float = 0.0
    motor_right: float = 0.0
    system_message: str = "Ready"
    last_update: float = 0.0

    def snapshot(self) -> dict:
        data = asdict(self)
        data["last_update"] = self.last_update or time.time()
        return data
