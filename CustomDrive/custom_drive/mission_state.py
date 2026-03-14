from __future__ import annotations

from enum import Enum


class MissionState(str, Enum):
    IDLE = "idle"
    DRIVE_TO_SEARCH_AREA = "drive_to_search_area"
    SCAN_FOR_TARGET = "scan_for_target"
    ALIGN_TO_TARGET = "align_to_target"
    APPROACH_TARGET = "approach_target"
    GRAB_TARGET = "grab_target"
    DRIVE_TO_DROP_ZONE = "drive_to_drop_zone"
    SCAN_FOR_DROP_ZONE = "scan_for_drop_zone"
    ALIGN_TO_DROP_ZONE = "align_to_drop_zone"
    APPROACH_DROP_ZONE = "approach_drop_zone"
    RELEASE_TARGET = "release_target"
    BACK_OUT = "back_out"
    COMPLETE = "complete"
    FAILED = "failed"
