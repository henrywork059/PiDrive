from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .config import RouteLeg
from .models import DriveCommand


class TimedRouteFollower:
    def __init__(self, routes: Dict[str, List[RouteLeg]]):
        self.routes = routes
        self.route_name: Optional[str] = None
        self.route_start_time: float = 0.0
        self.legs: List[RouteLeg] = []

    def start(self, route_name: str, now: float) -> None:
        if route_name not in self.routes:
            raise KeyError(f"Unknown route: {route_name}")
        self.route_name = route_name
        self.route_start_time = now
        self.legs = list(self.routes[route_name])

    def update(self, now: float) -> Tuple[bool, DriveCommand, Optional[str]]:
        if not self.route_name or not self.legs:
            return True, DriveCommand(note="route complete"), None

        elapsed = now - self.route_start_time
        spent = 0.0
        for leg in self.legs:
            if elapsed <= spent + leg.duration_s:
                return False, leg.command, leg.name
            spent += leg.duration_s

        return True, DriveCommand(note="route complete"), None
