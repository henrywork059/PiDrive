"""Deterministic differential-drive vehicle simulation for the PiSD emulator."""

from __future__ import annotations

import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from .environments import DEFAULT, validate_profile
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is required by PiSD itself
    np = None  # type: ignore[assignment]


TRACKS = {
    "straight": "Straight road",
    "left_curve": "Left curve",
    "right_curve": "Right curve",
    "s_curve": "S curve",
    "circle": "Circular track",
}


def _clamp(value: Any, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(low, min(high, number))


@dataclass(frozen=True)
class VehicleConfig:
    fixed_timestep_s: float = 1.0 / 60.0
    wheel_separation_m: float = 0.145
    max_speed_mps: float = 0.72
    acceleration_mps2: float = 1.5
    braking_mps2: float = 2.8
    motor_dead_zone: float = 0.035
    left_efficiency: float = 1.0
    right_efficiency: float = 1.0
    response_delay_s: float = 0.0
    road_width_m: float = 0.92
    seed: int = 41


class TrackPath:
    """Pre-sampled track centreline with a deterministic curvature profile."""

    def __init__(self, track_id: str, *, length_m: float = 240.0, step_m: float = 0.2, segments=None):
        if np is None:
            raise RuntimeError("PiSD Emulator requires NumPy. Install PiSD/requirements.txt first.")
        if track_id not in TRACKS and not (track_id == "custom" and segments):
            raise ValueError(f"Unknown track '{track_id}'. Available tracks: {', '.join(TRACKS)}")
        self.track_id = track_id
        self.segments = tuple(segments or ())
        if self.segments:
            length_m = sum(s["length_m"] for s in self.segments)
        self.step_m = float(step_m)
        count = int(length_m / step_m) + 1
        points = np.zeros((count, 2), dtype=np.float64)
        headings = np.zeros(count, dtype=np.float64)
        heading = 0.0  # zero faces forward along +Y
        for index in range(1, count):
            station = (index - 1) * step_m
            curvature = self._curvature(station)
            heading += curvature * step_m
            points[index, 0] = points[index - 1, 0] + math.sin(heading) * step_m
            points[index, 1] = points[index - 1, 1] + math.cos(heading) * step_m
            headings[index] = heading
        self.points = points
        self.headings = headings

    def _curvature(self, station_m: float) -> float:
        if self.track_id == "custom":
            end = 0.0
            for segment in self.segments:
                end += segment["length_m"]
                if station_m < end:
                    return segment["curvature"]
            return self.segments[-1]["curvature"]
        if self.track_id == "left_curve":
            return -0.11
        if self.track_id == "right_curve":
            return 0.11
        if self.track_id == "s_curve":
            return 0.11 if int(station_m // 15.0) % 2 == 0 else -0.11
        if self.track_id == "circle":
            return 0.16
        return 0.0

    def nearest(self, x: float, y: float) -> tuple[int, float, float]:
        delta = self.points - np.array((x, y), dtype=np.float64)
        index = int(np.argmin(np.einsum("ij,ij->i", delta, delta)))
        dx, dy = float(delta[index, 0]), float(delta[index, 1])
        heading = float(self.headings[index])
        # Positive offset is to the vehicle's right of the centreline.
        lateral = dx * math.cos(heading) - dy * math.sin(heading)
        return index, math.sqrt(dx * dx + dy * dy), lateral

    def ahead(self, index: int, *, distance_m: float = 42.0, stride_m: float = 0.35) -> list[tuple[float, float, float, float]]:
        stride = max(1, int(stride_m / self.step_m))
        end = min(len(self.points), index + int(distance_m / self.step_m) + 1)
        return [
            (float(i * self.step_m), float(self.points[i, 0]), float(self.points[i, 1]), float(self.headings[i]))
            for i in range(index, end, stride)
        ]

    def local_points(self, index: int, *, behind_m: float = 4.0, ahead_m: float = 24.0, stride_m: float = 0.5) -> list[list[float]]:
        stride = max(1, int(stride_m / self.step_m))
        start = max(0, index - int(behind_m / self.step_m))
        end = min(len(self.points), index + int(ahead_m / self.step_m) + 1)
        return [[round(float(point[0]), 3), round(float(point[1]), 3)] for point in self.points[start:end:stride]]


class VehicleEngine:
    """Runs a fixed-step vehicle model from PiSD's final logical wheel outputs."""

    def __init__(self, settings: dict[str, Any] | None = None):
        if np is None:
            raise RuntimeError("PiSD Emulator requires NumPy. Install PiSD/requirements.txt first.")
        supplied = dict(settings or {})
        self.config = VehicleConfig(
            wheel_separation_m=_clamp(supplied.get("wheel_separation_m"), 0.06, 0.5, 0.145),
            max_speed_mps=_clamp(supplied.get("max_speed_mps"), 0.1, 3.0, 0.72),
            acceleration_mps2=_clamp(supplied.get("acceleration_mps2"), 0.1, 8.0, 1.5),
            braking_mps2=_clamp(supplied.get("braking_mps2"), 0.1, 12.0, 2.8),
            motor_dead_zone=_clamp(supplied.get("motor_dead_zone"), 0.0, 0.4, 0.035),
            left_efficiency=_clamp(supplied.get("left_efficiency"), 0.1, 1.5, 1.0),
            right_efficiency=_clamp(supplied.get("right_efficiency"), 0.1, 1.5, 1.0),
            response_delay_s=_clamp(supplied.get("response_delay_s"), 0.0, 2.0, 0.0),
            road_width_m=_clamp(supplied.get("road_width_m"), 0.4, 4.0, 0.92),
            seed=int(_clamp(supplied.get("seed"), 0, 2_147_483_647, 41)),
        )
        self._lock = threading.RLock()
        self._track_id = "straight"
        self._custom_profile = None
        self._base_road_width = self.config.road_width_m
        self._path = TrackPath(self._track_id)
        self._obstacles = self._make_obstacles()
        self._x = 0.0
        self._y = 0.0
        self._heading = 0.0
        self._left_speed = 0.0
        self._right_speed = 0.0
        self._target_left = 0.0
        self._target_right = 0.0
        self._hardware_left = 0.0
        self._hardware_right = 0.0
        self._motor_config: dict[str, Any] = {}
        self._last_command: dict[str, Any] = {}
        self._command_history: deque[dict[str, Any]] = deque(maxlen=100)
        self._command_queue: deque[tuple[float, float, float]] = deque(maxlen=240)
        self._simulation_time = 0.0
        self._delayed_left = 0.0
        self._delayed_right = 0.0
        self._sim_speed = 1.0
        self._paused = False
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._physics_steps = 0
        self._tick_times: deque[float] = deque(maxlen=120)
        self._collision = False
        self._off_track = False
        self._actual_fps = 0.0
        self._last_tick_at = time.monotonic()
        self._reset_pose_locked()

    @property
    def fixed_timestep_s(self) -> float:
        return self.config.fixed_timestep_s

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="PiSD-Emulator-Physics", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self.set_motor_outputs({"left_intended": 0.0, "right_intended": 0.0, "left_hardware": 0.0, "right_hardware": 0.0, "command": {"mode": "emulator_shutdown"}})
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with self._lock:
            self._running = False
            self._thread = None
            self._left_speed = 0.0
            self._right_speed = 0.0

    def set_motor_outputs(self, payload: dict[str, Any]) -> None:
        """Receive already-mapped/safety-processed outputs from PiSD MotorService."""
        command = dict(payload.get("command") or {})
        now = time.monotonic()
        with self._lock:
            self._target_left = _clamp(payload.get("left_intended", payload.get("left_hardware", 0.0)), -1.0, 1.0, 0.0)
            self._target_right = _clamp(payload.get("right_intended", payload.get("right_hardware", 0.0)), -1.0, 1.0, 0.0)
            self._hardware_left = _clamp(payload.get("left_hardware", 0.0), -1.0, 1.0, 0.0)
            self._hardware_right = _clamp(payload.get("right_hardware", 0.0), -1.0, 1.0, 0.0)
            self._motor_config = dict(payload.get("config") or {})
            self._last_command = command
            self._command_queue.append((self._simulation_time, self._target_left, self._target_right))
            self._command_history.append({
                "at_monotonic": now,
                "left_intended": self._target_left,
                "right_intended": self._target_right,
                "left_hardware": self._hardware_left,
                "right_hardware": self._hardware_right,
                "command": command,
            })

    def change_track(self, track_id: str) -> None:
        if track_id not in TRACKS:
            raise ValueError(f"Unknown track '{track_id}'.")
        with self._lock:
            self._track_id = track_id
            self._custom_profile = None
            self.config = replace(self.config, road_width_m=self._base_road_width)
            self._path = TrackPath(track_id)
            self._obstacles = self._make_obstacles()
            self._target_left = self._target_right = 0.0
            self._hardware_left = self._hardware_right = 0.0
            self._command_queue.clear()
            self._reset_pose_locked()

    def configure_environment(self, profile) -> None:
        candidate = validate_profile(profile)
        path = TrackPath("custom", segments=candidate["segments"])
        with self._lock:
            if self._running:
                raise ValueError("Stop the engine before changing custom environment.")
            self._track_id = "custom"
            self._custom_profile = candidate
            self.config = replace(self.config, road_width_m=candidate["road_width_m"])
            self._path = path
            self._obstacles = [dict(o) for o in candidate["obstacles"]]
            self._target_left = self._target_right = 0.0
            self._hardware_left = self._hardware_right = 0.0
            self._reset_pose_locked()

    def disconnect_motor_outputs(self) -> None:
        """Fail closed at the simulated actuator, including delayed commands."""
        with self._lock:
            self._target_left = self._target_right = 0.0
            self._hardware_left = self._hardware_right = 0.0
            self._delayed_left = self._delayed_right = 0.0
            self._command_queue.clear()
            self._last_command = {"mode": "virtual_motor_disconnected"}

    def reset(self) -> None:
        with self._lock:
            self._target_left = self._target_right = 0.0
            self._hardware_left = self._hardware_right = 0.0
            self._command_queue.clear()
            self._last_command = {"mode": "reset"}
            self._reset_pose_locked()

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = bool(paused)
            if self._paused:
                self._left_speed = 0.0
                self._right_speed = 0.0

    def set_speed_scale(self, scale: Any) -> float:
        with self._lock:
            self._sim_speed = _clamp(scale, 0.25, 3.0, self._sim_speed)
            return self._sim_speed

    def step(self, count: int = 1) -> None:
        """Advance the deterministic model by ``count`` fixed simulation steps."""
        for _ in range(max(0, min(int(count), 10_000))):
            with self._lock:
                self._step_locked(self.config.fixed_timestep_s, force=True)

    def _reset_pose_locked(self) -> None:
        self._x = float(self._path.points[0, 0])
        self._y = float(self._path.points[0, 1])
        self._heading = float(self._path.headings[0])
        self._left_speed = 0.0
        self._right_speed = 0.0
        self._collision = False
        self._off_track = False
        self._physics_steps = 0
        self._simulation_time = 0.0
        self._delayed_left = 0.0
        self._delayed_right = 0.0
        self._command_queue.clear()
        self._last_tick_at = time.monotonic()

    def _make_obstacles(self) -> list[dict[str, Any]]:
        random_source = random.Random(self.config.seed)
        obstacles = []
        for station in range(10, 220, 17):
            obstacles.append({
                "station_m": float(station),
                "lateral_m": random_source.choice((-1.0, 1.0)) * random_source.uniform(0.20, 0.31),
                "kind": random_source.choice(("cone", "bollard")),
            })
        return obstacles

    def _run_loop(self) -> None:
        timestep = self.config.fixed_timestep_s
        previous = time.perf_counter()
        accumulator = 0.0
        while not self._stop_event.is_set():
            now = time.perf_counter()
            elapsed = min(now - previous, 0.2)
            previous = now
            with self._lock:
                speed_scale = self._sim_speed
                paused = self._paused
            if paused:
                accumulator = 0.0
            else:
                accumulator += elapsed * speed_scale
                while accumulator >= timestep:
                    self.step(1)
                    accumulator -= timestep
            wait_for = max(0.001, (timestep - accumulator) / max(speed_scale, 0.01))
            self._stop_event.wait(min(wait_for, 0.02))

    def _approach(self, current: float, target: float, amount: float) -> float:
        if target > current:
            return min(target, current + amount)
        return max(target, current - amount)

    def _delayed_targets_locked(self) -> tuple[float, float]:
        cutoff = self._simulation_time - self.config.response_delay_s
        while self._command_queue and self._command_queue[0][0] <= cutoff:
            _, self._delayed_left, self._delayed_right = self._command_queue.popleft()
        return self._delayed_left, self._delayed_right

    def _step_locked(self, dt: float, *, force: bool = False) -> None:
        if self._paused and not force:
            return
        target_left, target_right = self._delayed_targets_locked()
        dead_zone = self.config.motor_dead_zone
        if abs(target_left) <= dead_zone:
            target_left = 0.0
        if abs(target_right) <= dead_zone:
            target_right = 0.0
        target_left = max(-1.0, min(1.0, target_left * self.config.left_efficiency)) * self.config.max_speed_mps
        target_right = max(-1.0, min(1.0, target_right * self.config.right_efficiency)) * self.config.max_speed_mps
        for name, target in (("left", target_left), ("right", target_right)):
            current = self._left_speed if name == "left" else self._right_speed
            rate = self.config.braking_mps2 if abs(target) < abs(current) or current * target < 0 else self.config.acceleration_mps2
            result = self._approach(current, target, rate * dt)
            if name == "left":
                self._left_speed = result
            else:
                self._right_speed = result

        velocity = (self._left_speed + self._right_speed) * 0.5
        # Heading is measured clockwise from +Y (a positive value turns right),
        # so the faster left wheel is the outside wheel of a right-hand turn.
        angular_velocity = (self._left_speed - self._right_speed) / self.config.wheel_separation_m
        mid_heading = self._heading + angular_velocity * dt * 0.5
        self._x += velocity * math.sin(mid_heading) * dt
        self._y += velocity * math.cos(mid_heading) * dt
        self._heading = (self._heading + angular_velocity * dt + math.pi) % (2.0 * math.pi) - math.pi
        nearest, _, lateral = self._path.nearest(self._x, self._y)
        self._off_track = abs(lateral) > self.config.road_width_m * 0.5
        station = nearest * self._path.step_m
        self._collision = self._has_obstacle_collision_locked(nearest, station)
        self._physics_steps += 1
        self._simulation_time += dt
        now = time.monotonic()
        self._tick_times.append(now)
        if len(self._tick_times) > 1:
            span = self._tick_times[-1] - self._tick_times[0]
            if span > 0:
                self._actual_fps = round((len(self._tick_times) - 1) / span, 1)
        self._last_tick_at = now

    def _has_obstacle_collision_locked(self, nearest: int, station: float) -> bool:
        # Obstacles are static in track coordinates and use the configured seed.
        if station < 6.0:
            return False
        for obstacle in self._obstacles:
            obstacle_station = float(obstacle["station_m"])
            if abs(station - obstacle_station) < 0.55:
                lateral = float(obstacle["lateral_m"])
                index = min(len(self._path.points) - 1, int(obstacle_station / self._path.step_m))
                point = self._path.points[index]
                heading = self._path.headings[index]
                ox = float(point[0]) + math.cos(float(heading)) * lateral
                oy = float(point[1]) - math.sin(float(heading)) * lateral
                if math.hypot(self._x - ox, self._y - oy) < 0.32:
                    return True
        return False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            nearest, distance, lateral = self._path.nearest(self._x, self._y)
            track_points = self._path.local_points(nearest)
            obstacle_points = []
            for obstacle in self._obstacles:
                if obstacle["station_m"] < max(0.0, nearest * self._path.step_m - 2.0) or obstacle["station_m"] > nearest * self._path.step_m + 25.0:
                    continue
                obstacle_index = min(len(self._path.points) - 1, int(obstacle["station_m"] / self._path.step_m))
                obstacle_heading = float(self._path.headings[obstacle_index])
                obstacle_center = self._path.points[obstacle_index]
                obstacle_lateral = float(obstacle["lateral_m"])
                obstacle_points.append({
                    "x_m": round(float(obstacle_center[0]) + math.cos(obstacle_heading) * obstacle_lateral, 3),
                    "y_m": round(float(obstacle_center[1]) - math.sin(obstacle_heading) * obstacle_lateral, 3),
                    "kind": obstacle["kind"],
                })
            gpio = self._gpio_snapshot_locked()
            return {
                "mode": "emulator" if self._running else "emulator_stopped",
                "running": self._running,
                "paused": self._paused,
                "track_id": self._track_id,
                "track_name": self._custom_profile["name"] if self._custom_profile else TRACKS[self._track_id],
                "environment": {key: self._custom_profile[key] for key in DEFAULT} if self._custom_profile else dict(DEFAULT),
                "track_points": track_points,
                "obstacles": obstacle_points,
                "road_width_m": self.config.road_width_m,
                "vehicle": {
                    "x_m": round(self._x, 4),
                    "y_m": round(self._y, 4),
                    "heading_rad": round(self._heading, 5),
                    "heading_deg": round(math.degrees(self._heading), 2),
                    "speed_mps": round((self._left_speed + self._right_speed) * 0.5, 4),
                    "left_wheel_mps": round(self._left_speed, 4),
                    "right_wheel_mps": round(self._right_speed, 4),
                    "cross_track_m": round(lateral, 4),
                    "off_track": self._off_track,
                    "collision": self._collision,
                },
                "motor": {
                    "left_intended": round(self._target_left, 4),
                    "right_intended": round(self._target_right, 4),
                    "left_hardware": round(self._hardware_left, 4),
                    "right_hardware": round(self._hardware_right, 4),
                    "last_command": dict(self._last_command),
                    "virtual_gpio": gpio,
                    "pwm_frequency_hz": int(self._motor_config.get("pwm_frequency_hz", 1000) or 1000),
                },
                "physics": {
                    "fixed_timestep_s": self.config.fixed_timestep_s,
                    "steps": self._physics_steps,
                    "actual_fps": self._actual_fps,
                    "speed_scale": self._sim_speed,
                    "config": {
                        "wheel_separation_m": self.config.wheel_separation_m,
                        "max_speed_mps": self.config.max_speed_mps,
                        "acceleration_mps2": self.config.acceleration_mps2,
                        "braking_mps2": self.config.braking_mps2,
                        "motor_dead_zone": self.config.motor_dead_zone,
                        "left_efficiency": self.config.left_efficiency,
                        "right_efficiency": self.config.right_efficiency,
                        "response_delay_s": self.config.response_delay_s,
                    },
                },
                "camera": {
                    "source": "PiSD CameraService frame_provider",
                    "rendering": "projected virtual road geometry",
                    "supported_settings": ["width", "height", "fps", "brightness", "contrast", "saturation", "hflip", "vflip"],
                    "unsupported_hardware_settings": ["analogue_gain", "sensor_mode", "physical_exposure", "physical_white_balance"],
                },
                "track_distance_m": round(nearest * self._path.step_m, 3),
                "distance_to_centre_m": round(distance, 3),
            }

    def _gpio_snapshot_locked(self) -> list[dict[str, Any]]:
        config = self._motor_config
        pins = {
            "left": config.get("left_pins", [17, 27]),
            "right": config.get("right_pins", [22, 23]),
        }
        outputs = {"left": self._hardware_left, "right": self._hardware_right}
        result: list[dict[str, Any]] = []
        for side in ("left", "right"):
            try:
                forward_pin, reverse_pin = int(pins[side][0]), int(pins[side][1])
            except (TypeError, ValueError, IndexError):
                forward_pin, reverse_pin = ((17, 27) if side == "left" else (22, 23))
            value = outputs[side]
            result.extend((
                {"pin": forward_pin, "function": f"{side}_forward_pwm", "state": "PWM" if value > 0 else "LOW", "duty_cycle_percent": round(max(value, 0.0) * 100.0, 1)},
                {"pin": reverse_pin, "function": f"{side}_reverse_pwm", "state": "PWM" if value < 0 else "LOW", "duty_cycle_percent": round(max(-value, 0.0) * 100.0, 1)},
            ))
        return result


__all__ = ["TRACKS", "TrackPath", "VehicleConfig", "VehicleEngine"]
