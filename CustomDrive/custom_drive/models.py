from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center_x(self) -> float:
        return self.x1 + self.width * 0.5

    @property
    def center_y(self) -> float:
        return self.y1 + self.height * 0.5

    @property
    def bottom_center_x(self) -> float:
        return self.center_x

    @property
    def bottom_center_y(self) -> float:
        return self.y2

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    box: BoundingBox


@dataclass(slots=True)
class FramePerception:
    frame_width: int
    frame_height: int
    detections: List[Detection] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def frame_area(self) -> float:
        return float(self.frame_width * self.frame_height)


@dataclass(slots=True)
class DriveCommand:
    steering: float = 0.0
    throttle: float = 0.0
    note: str = ""


@dataclass(slots=True)
class MissionSnapshot:
    state: str
    detail: str
    retries: int
    completed_cycles: int
    last_command: DriveCommand
    active_route_leg: Optional[str] = None
