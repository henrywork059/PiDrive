"""First-person virtual road renderer using Pillow and NumPy."""

from __future__ import annotations

import math
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - NumPy is required by PiSD itself
    np = None  # type: ignore[assignment]

try:
    from PIL import Image, ImageDraw, ImageEnhance
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PiSD Emulator requires Pillow. Install PiSD/requirements.txt first.") from exc

from .engine import VehicleEngine


def _number(settings: Any, name: str, default: float) -> float:
    try:
        value = float(getattr(settings, name, default))
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


class RoadRenderer:
    """Builds an RGB road scene then returns PiSD's expected BGR array."""

    def render(self, engine: VehicleEngine, settings: Any) -> Any:
        if np is None:
            raise RuntimeError("PiSD Emulator requires NumPy. Install PiSD/requirements.txt first.")
        width = max(64, min(1920, int(_number(settings, "width", 426))))
        height = max(48, min(1080, int(_number(settings, "height", 240))))
        state = engine.snapshot()
        vehicle = state["vehicle"]
        camera_x = float(vehicle["x_m"])
        camera_y = float(vehicle["y_m"])
        camera_heading = float(vehicle["heading_rad"])
        road_width = float(state["road_width_m"])
        points = state["track_points"]
        environment = state["environment"]

        horizon = int(height * 0.37)
        fov = math.radians(62.0)
        focal = width / (2.0 * math.tan(fov * 0.5))
        camera_height_m = 0.17
        image = Image.new("RGB", (width, height), (151, 190, 211))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, horizon, width, height), fill=(113, 133, 87))
        draw.rectangle((0, horizon - 2, width, horizon + 1), fill=(72, 101, 71))

        projected: list[tuple[float, float, float, float, float]] = []
        forward_sin = math.sin(camera_heading)
        forward_cos = math.cos(camera_heading)
        for station, world_x, world_y in self._track_world_samples(engine, points):
            dx = world_x - camera_x
            dy = world_y - camera_y
            lateral = dx * forward_cos - dy * forward_sin
            forward = dx * forward_sin + dy * forward_cos
            if forward <= 0.25:
                continue
            scale = focal / forward
            screen_x = width * 0.5 + lateral * scale
            screen_y = horizon + camera_height_m * scale
            projected.append((station, forward, screen_x, screen_y, scale))

        if len(projected) >= 2:
            half = road_width * 0.5
            left_edge = [(px - half * scale, py) for _, _, px, py, scale in projected]
            right_edge = [(px + half * scale, py) for _, _, px, py, scale in projected]
            road_polygon = left_edge + list(reversed(right_edge))
            draw.polygon(road_polygon, fill=(80, 83, 86))
            self._draw_scenery(draw, width, height, horizon, focal, camera_height_m, engine, camera_x, camera_y, camera_heading, points)
            if environment["edge_lines"]:
                self._draw_edge_lines(draw, projected, half)
            if environment["markings"] != "none":
                self._draw_lane_markers(draw, projected, solid=environment["markings"] == "solid")
            self._draw_obstacles(draw, engine, projected, width, horizon, camera_height_m, focal, camera_x, camera_y, camera_heading)
            self._draw_road_texture(draw, projected, road_width)

        lighting = {"day":1.0,"dusk":.58,"night":.27}[environment["lighting"]]
        if lighting != 1.0:
            image = ImageEnhance.Brightness(image).enhance(lighting)
            draw = ImageDraw.Draw(image)

        # Camera status stays legible in PiSD's existing preview, while the scene
        # itself is generated from the vehicle's current world pose.
        distance = float(state["track_distance_m"])
        label = f"{state['track_name']}  {distance:05.1f} m"
        draw.rounded_rectangle((6, 6, min(width - 6, 190), 24), radius=4, fill=(24, 30, 34))
        draw.text((11, 10), label, fill=(242, 245, 245))

        brightness = max(0.1, min(2.0, 1.0 + _number(settings, "brightness", 0.0) * 0.5))
        contrast = max(0.1, min(2.0, _number(settings, "contrast", 1.0)))
        saturation = max(0.0, min(2.0, _number(settings, "saturation", 1.0)))
        if brightness != 1.0:
            image = ImageEnhance.Brightness(image).enhance(brightness)
        if contrast != 1.0:
            image = ImageEnhance.Contrast(image).enhance(contrast)
        if saturation != 1.0:
            image = ImageEnhance.Color(image).enhance(saturation)
        if bool(getattr(settings, "hflip", False)):
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if bool(getattr(settings, "vflip", False)):
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        rgb = np.asarray(image, dtype=np.uint8)
        return rgb[:, :, ::-1].copy()

    def _track_world_samples(self, engine: VehicleEngine, points: list[list[float]]) -> list[tuple[float, float, float]]:
        # The engine status returns world points for the top-down panel. Use the
        # track's pre-sampled path for perspective and retain station order.
        snapshot = engine.snapshot()
        nearest = int(round(float(snapshot["track_distance_m"]) / engine._path.step_m))
        return [(station, x, y) for station, x, y, _ in engine._path.ahead(nearest, distance_m=42.0, stride_m=0.35)]

    def _draw_edge_lines(self, draw: Any, projected: list[tuple[float, float, float, float, float]], half_width: float) -> None:
        for side, color in ((-1.0, (215, 219, 207)), (1.0, (215, 219, 207))):
            line = [(x + side * half_width * scale, y) for _, forward, x, y, scale in projected if forward > 0.4]
            if len(line) >= 2:
                draw.line(line, fill=color, width=2)

    def _draw_lane_markers(self, draw: Any, projected: list[tuple[float, float, float, float, float]], *, solid=False) -> None:
        for first, second in zip(projected, projected[1:]):
            station, forward, x1, y1, scale = first
            next_station, next_forward, x2, y2, _ = second
            dash_position = station % 7.0
            if forward <= 1.5 or next_forward <= 1.5 or (not solid and not 1.5 <= dash_position < 2.3):
                continue
            marker_width = max(1, min(7, int(0.07 * scale)))
            draw.line((x1, y1, x2, y2), fill=(228, 200, 66), width=marker_width)

    def _draw_scenery(self, draw: Any, width: int, height: int, horizon: int, focal: float, camera_height: float, engine: VehicleEngine, camera_x: float, camera_y: float, camera_heading: float, points: list[list[float]]) -> None:
        path = engine._path
        nearest = int(round(engine.snapshot()["track_distance_m"] / path.step_m))
        start_station = nearest * path.step_m
        for distance in range(7, 43, 6):
            index = min(len(path.points) - 1, nearest + int(distance / path.step_m))
            point = path.points[index]
            heading = float(path.headings[index])
            for side in (-1.0, 1.0):
                # Small stylised roadside posts and foliage provide depth cues.
                lateral = side * (engine.config.road_width_m * 0.5 + 1.2 + ((index // 7) % 3) * 0.35)
                world_x = float(point[0]) + math.cos(heading) * lateral
                world_y = float(point[1]) - math.sin(heading) * lateral
                dx, dy = world_x - camera_x, world_y - camera_y
                rel_x = dx * math.cos(camera_heading) - dy * math.sin(camera_heading)
                rel_y = dx * math.sin(camera_heading) + dy * math.cos(camera_heading)
                if rel_y <= 0.7:
                    continue
                scale = focal / rel_y
                sx = width * 0.5 + rel_x * scale
                ground_y = horizon + camera_height * scale
                size = max(2, min(42, int(0.48 * scale)))
                if sx < -size or sx > width + size or ground_y < horizon or ground_y > height + size:
                    continue
                if (index // 2) % 2:
                    draw.polygon(((sx, ground_y - size * 2), (sx - size, ground_y), (sx + size, ground_y)), fill=(63, 100, 58))
                    draw.rectangle((sx - 1, ground_y - 4, sx + 1, ground_y + 2), fill=(92, 74, 57))
                else:
                    draw.rectangle((sx - 1, ground_y - size * 1.2, sx + 1, ground_y), fill=(221, 226, 216))
                    draw.rectangle((sx - size * 0.32, ground_y - size * 1.2, sx + size * 0.32, ground_y - size * 0.6), fill=(194, 68, 47))

    def _draw_obstacles(
        self,
        draw: Any,
        engine: VehicleEngine,
        projected: list[tuple[float, float, float, float, float]],
        width: int,
        horizon: int,
        camera_height: float,
        focal: float,
        camera_x: float,
        camera_y: float,
        camera_heading: float,
    ) -> None:
        path = engine._path
        nearest = int(round(engine.snapshot()["track_distance_m"] / path.step_m))
        for obstacle in engine._obstacles:
            obstacle_station = float(obstacle["station_m"])
            ahead = obstacle_station - nearest * path.step_m
            if ahead < 0.8 or ahead > 42:
                continue
            index = min(len(path.points) - 1, int(obstacle_station / path.step_m))
            point = path.points[index]
            heading = float(path.headings[index])
            lateral = float(obstacle["lateral_m"])
            world_x = float(point[0]) + math.cos(heading) * lateral
            world_y = float(point[1]) - math.sin(heading) * lateral
            dx, dy = world_x - camera_x, world_y - camera_y
            rel_x = dx * math.cos(camera_heading) - dy * math.sin(camera_heading)
            rel_y = dx * math.sin(camera_heading) + dy * math.cos(camera_heading)
            if rel_y <= 0.5:
                continue
            scale = focal / rel_y
            sx = width * 0.5 + rel_x * scale
            sy = max(0.0, min(1000.0, horizon + camera_height * scale))
            size = max(2, min(36, int(0.11 * scale)))
            if sx < -size or sx > width + size:
                continue
            draw.polygon(((sx, sy - size * 2), (sx - size, sy), (sx + size, sy)), fill=(239, 109, 37), outline=(44, 43, 41))

    def _draw_road_texture(self, draw: Any, projected: list[tuple[float, float, float, float, float]], road_width: float) -> None:
        for station, forward, x, y, scale in projected:
            if int(station * 10.0) % 23 != 0 or forward < 1.0:
                continue
            line_width = max(1, min(3, int(scale * 0.007)))
            half_road_px = road_width * 0.5 * scale
            draw.line((x - half_road_px, y, x + half_road_px, y), fill=(87, 89, 91), width=line_width)


__all__ = ["RoadRenderer"]
