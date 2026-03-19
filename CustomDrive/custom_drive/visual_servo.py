from __future__ import annotations

from typing import Optional

from .config import MissionConfig
from .models import Detection, DriveCommand, FramePerception


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def select_best_detection(
    perception: FramePerception,
    label: str,
    min_confidence: float,
) -> Optional[Detection]:
    matches = [
        det for det in perception.detections
        if det.label == label and det.confidence >= min_confidence
    ]
    if not matches:
        return None
    return max(matches, key=lambda det: det.confidence * max(1.0, det.box.area))


class VisualServoController:
    def __init__(self, config: MissionConfig):
        self.config = config

    def x_error_ratio(self, det: Detection, perception: FramePerception) -> float:
        frame_center_x = perception.frame_width * 0.5
        x_err_px = det.box.bottom_center_x - frame_center_x
        return x_err_px / max(1.0, frame_center_x)

    def bottom_ratio(self, det: Detection, perception: FramePerception) -> float:
        return det.box.bottom_center_y / max(1.0, perception.frame_height)

    def area_ratio(self, det: Detection, perception: FramePerception) -> float:
        return det.box.area / max(1.0, perception.frame_area)

    def is_centered(self, det: Detection, perception: FramePerception) -> bool:
        return abs(self.x_error_ratio(det, perception)) <= self.config.align_tolerance_ratio

    def is_close_for_pickup(self, det: Detection, perception: FramePerception) -> bool:
        return (
            self.bottom_ratio(det, perception) >= self.config.pickup_bottom_ratio
            or self.area_ratio(det, perception) >= self.config.pickup_area_ratio
        )

    def is_close_for_drop(self, det: Detection, perception: FramePerception) -> bool:
        return (
            self.bottom_ratio(det, perception) >= self.config.drop_bottom_ratio
            or self.area_ratio(det, perception) >= self.config.drop_area_ratio
        )

    def search_command(self, note: str) -> DriveCommand:
        return DriveCommand(
            steering=self.config.scan_spin_steering,
            throttle=0.0,
            note=note,
        )

    def align_command(self, det: Detection, perception: FramePerception, note: str) -> DriveCommand:
        err = self.x_error_ratio(det, perception)
        steering = clamp(err * self.config.align_kp, -self.config.max_steering, self.config.max_steering)
        return DriveCommand(
            steering=steering,
            throttle=0.0,
            note=f"{note} | x_err={err:+.3f}",
        )

    def approach_command(self, det: Detection, perception: FramePerception, note: str) -> DriveCommand:
        err = self.x_error_ratio(det, perception)
        steering = clamp(err * self.config.align_kp, -self.config.max_steering, self.config.max_steering)
        if abs(err) > self.config.align_tolerance_ratio:
            return DriveCommand(steering=steering, throttle=0.0, note=f"{note} | re-center first")

        tight_center = abs(err) <= max(0.02, self.config.align_tolerance_ratio * 0.5)
        speed = self.config.final_approach_speed if tight_center else self.config.approach_speed
        return DriveCommand(steering=steering, throttle=speed, note=f"{note} | x_err={err:+.3f}")

    def back_out_command(self) -> DriveCommand:
        return DriveCommand(steering=0.0, throttle=-0.16, note="back out")
