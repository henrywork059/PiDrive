from __future__ import annotations

from typing import Protocol


class RobotInterface(Protocol):
    def now(self) -> float:
        ...

    def set_drive(self, steering: float, throttle: float, note: str = "") -> None:
        ...

    def stop(self, note: str = "") -> None:
        ...

    def pickup_sequence(self) -> bool:
        ...

    def release_sequence(self) -> bool:
        ...
