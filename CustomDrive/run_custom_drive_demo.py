from __future__ import annotations

import math
import time

from custom_drive import BoundingBox, Detection, FramePerception, MissionConfig, MissionController
from custom_drive.fake_robot import FakeRobot
from custom_drive.mission_state import MissionState

FRAME_W = 640
FRAME_H = 360


def make_detection(label: str, cx_ratio: float, bottom_ratio: float, box_w: int = 80, box_h: int = 80, confidence: float = 0.92):
    cx = cx_ratio * FRAME_W
    bottom = bottom_ratio * FRAME_H
    x1 = cx - box_w / 2
    x2 = cx + box_w / 2
    y2 = bottom
    y1 = y2 - box_h
    return Detection(
        label=label,
        confidence=confidence,
        box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )


def scripted_perception(controller: MissionController) -> FramePerception:
    state = controller.state
    t = controller.state_elapsed()
    detections = []

    if state == MissionState.SCAN_FOR_TARGET and t > 1.5:
        detections = [make_detection("he3", cx_ratio=0.78, bottom_ratio=0.58)]
    elif state == MissionState.ALIGN_TO_TARGET:
        cx_ratio = max(0.5, 0.78 - t * 0.18)
        detections = [make_detection("he3", cx_ratio=cx_ratio, bottom_ratio=0.60)]
    elif state == MissionState.APPROACH_TARGET:
        bottom_ratio = min(0.90, 0.60 + t * 0.15)
        cx_ratio = 0.5 + math.sin(t * 4.0) * 0.015
        detections = [make_detection("he3", cx_ratio=cx_ratio, bottom_ratio=bottom_ratio, box_w=92, box_h=92)]
    elif state == MissionState.SCAN_FOR_DROP_ZONE and t > 1.3:
        detections = [make_detection("he3_zone", cx_ratio=0.25, bottom_ratio=0.45, box_w=110, box_h=70)]
    elif state == MissionState.ALIGN_TO_DROP_ZONE:
        cx_ratio = min(0.5, 0.25 + t * 0.20)
        detections = [make_detection("he3_zone", cx_ratio=cx_ratio, bottom_ratio=0.48, box_w=118, box_h=74)]
    elif state == MissionState.APPROACH_DROP_ZONE:
        bottom_ratio = min(0.82, 0.48 + t * 0.14)
        cx_ratio = 0.5 + math.sin(t * 3.0) * 0.012
        detections = [make_detection("he3_zone", cx_ratio=cx_ratio, bottom_ratio=bottom_ratio, box_w=130, box_h=82)]

    return FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=detections, timestamp=time.monotonic())


def main() -> None:
    robot = FakeRobot()
    config = MissionConfig(max_cycles=2)
    controller = MissionController(robot=robot, config=config)
    controller.start()

    last_state = None
    print("=== CustomDrive demo started ===")

    while controller.state not in (MissionState.COMPLETE, MissionState.FAILED):
        perception = scripted_perception(controller)
        snapshot = controller.update(perception)

        if snapshot.state != last_state:
            print(f"\n[STATE] {snapshot.state} | detail={snapshot.detail} | retries={snapshot.retries} | cycles={snapshot.completed_cycles}")
            last_state = snapshot.state

        print(
            f"  cmd: steering={snapshot.last_command.steering:+.2f} "
            f"throttle={snapshot.last_command.throttle:+.2f} "
            f"note={snapshot.last_command.note}"
        )
        time.sleep(0.2)

    print(f"\n=== Demo finished with state: {controller.state.value} ===")
    print(f"Completed cycles: {controller.completed_cycles}")


if __name__ == "__main__":
    main()
