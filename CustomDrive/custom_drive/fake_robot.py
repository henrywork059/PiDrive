from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List

from .models import DriveCommand


@dataclass(slots=True)
class RobotLogEntry:
    timestamp: float
    action: str
    detail: str


@dataclass
class FakeRobot:
    started_at: float = field(default_factory=time.monotonic)
    history: List[RobotLogEntry] = field(default_factory=list)
    last_command: DriveCommand = field(default_factory=DriveCommand)
    has_payload: bool = False

    def now(self) -> float:
        return time.monotonic() - self.started_at

    def set_drive(self, steering: float, throttle: float, note: str = "") -> None:
        self.last_command = DriveCommand(steering=steering, throttle=throttle, note=note)
        self.history.append(RobotLogEntry(self.now(), "drive", f"steering={steering:+.2f}, throttle={throttle:+.2f}, note={note}"))

    def stop(self, note: str = "") -> None:
        self.last_command = DriveCommand(steering=0.0, throttle=0.0, note=note)
        self.history.append(RobotLogEntry(self.now(), "stop", note))

    def pickup_sequence(self) -> bool:
        self.has_payload = True
        self.history.append(RobotLogEntry(self.now(), "pickup", "pickup sequence succeeded"))
        return True

    def release_sequence(self) -> bool:
        if not self.has_payload:
            self.history.append(RobotLogEntry(self.now(), "release", "release failed: no payload"))
            return False
        self.has_payload = False
        self.history.append(RobotLogEntry(self.now(), "release", "release sequence succeeded"))
        return True
