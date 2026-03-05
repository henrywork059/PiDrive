# control_state.py
"""Control state helpers.

This module centralises the default control state in one place so that
future changes (adding new fields, renaming keys) only need to touch
this file, rather than updating literals scattered across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import time


@dataclass
class ControlState:
    """Represents the current control state of the Pi-Car.

    The rest of the system is still using a plain ``dict`` for backward
    compatibility, but this dataclass documents the expected fields and
    types in one place.
    """

    steering: float = 0.0
    throttle: float = 0.0
    mode: str = "manual"
    last_update: float = 0.0


def make_initial_state() -> Dict[str, Any]:
    """Return a fresh control state dict with default values."""
    now = time.time()
    return {
        "steering": 0.0,
        "throttle": 0.0,
        "mode": "manual",
        "last_update": now,
    }
