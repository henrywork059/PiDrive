from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .models import DriveCommand


@dataclass(slots=True)
class RouteLeg:
    name: str
    duration_s: float
    command: DriveCommand


@dataclass(slots=True)
class MissionConfig:
    target_label: str = "he3"
    drop_zone_label: str = "he3_zone"
    min_confidence: float = 0.45

    # Vision control
    align_kp: float = 0.85
    max_steering: float = 0.7
    align_tolerance_ratio: float = 0.07
    center_hold_frames: int = 3
    scan_spin_steering: float = 0.45
    search_timeout_s: float = 10.0

    # Approach tuning
    approach_speed: float = 0.22
    final_approach_speed: float = 0.12
    pickup_bottom_ratio: float = 0.84
    pickup_area_ratio: float = 0.18
    drop_bottom_ratio: float = 0.76
    drop_area_ratio: float = 0.14

    # Mission control
    max_retries_per_stage: int = 2
    enable_repeat: bool = True
    max_cycles: int = 2

    # Coarse fixed routes: draft only. Calibrate on the real field later.
    routes: Dict[str, List[RouteLeg]] = field(default_factory=lambda: {
        "to_search_area": [
            RouteLeg("leave_start", 1.2, DriveCommand(steering=0.0, throttle=0.28, note="leave start")),
            RouteLeg("pass_obstacle_lane", 1.4, DriveCommand(steering=0.10, throttle=0.24, note="coarse obstacle pass")),
            RouteLeg("enter_scan_pose", 0.7, DriveCommand(steering=-0.18, throttle=0.18, note="enter search pose")),
        ],
        "to_drop_zone": [
            RouteLeg("exit_pick_zone", 0.6, DriveCommand(steering=0.0, throttle=-0.15, note="back off after grab")),
            RouteLeg("turn_to_return", 0.8, DriveCommand(steering=-0.45, throttle=0.0, note="turn toward return route")),
            RouteLeg("drive_to_storage_area", 1.6, DriveCommand(steering=0.06, throttle=0.26, note="coarse drive to storage area")),
            RouteLeg("enter_drop_scan_pose", 0.7, DriveCommand(steering=0.18, throttle=0.16, note="enter drop scan pose")),
        ],
    })
