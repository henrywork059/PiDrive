from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import time


@dataclass
class PiCarRobotBridge:
    """Draft adapter for the current PiCar stack.

    Replace or extend this class when you integrate CustomDrive into PiServer.

    Expected existing modules from your PiCar codebase:
    - motor_controller.py -> MotorController.update(steering, throttle, mode)
    - camera.py           -> camera.get_latest_frame() or camera.get_frame()

    Missing on purpose in this draft:
    - real gripper / arm controller
    - pickup success sensor
    - release success sensor
    """

    motor: Any
    arm: Optional[Any] = None
    mode_name: str = "custom_drive"
    started_at: float = time.monotonic()

    def now(self) -> float:
        return time.monotonic() - self.started_at

    def set_drive(self, steering: float, throttle: float, note: str = "") -> None:
        self.motor.update(steering=steering, throttle=throttle, mode=self.mode_name)
        print(f"[CUSTOM DRIVE] steering={steering:+.2f} throttle={throttle:+.2f} note={note}")

    def stop(self, note: str = "") -> None:
        self.motor.update(steering=0.0, throttle=0.0, mode=self.mode_name)
        print(f"[CUSTOM DRIVE] stop | {note}")

    def pickup_sequence(self) -> bool:
        if self.arm is None:
            print("[CUSTOM DRIVE] pickup_sequence() placeholder called. No arm bound yet.")
            return False
        # Replace these calls with your real arm API.
        self.arm.open()
        self.arm.lower()
        self.arm.close()
        self.arm.raise_up()
        return True

    def release_sequence(self) -> bool:
        if self.arm is None:
            print("[CUSTOM DRIVE] release_sequence() placeholder called. No arm bound yet.")
            return False
        self.arm.lower()
        self.arm.open()
        self.arm.raise_up()
        return True
