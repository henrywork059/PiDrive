from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class YoloBox:
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

    def clamp(self) -> "YoloBox":
        self.x_center = min(max(self.x_center, 0.0), 1.0)
        self.y_center = min(max(self.y_center, 0.0), 1.0)
        self.width = min(max(self.width, 0.0), 1.0)
        self.height = min(max(self.height, 0.0), 1.0)
        return self


@dataclass
class PixelBox:
    class_id: int
    x1: float
    y1: float
    x2: float
    y2: float


def read_yolo_label_file(path: Path) -> List[YoloBox]:
    if not path.exists():
        return []
    items: List[YoloBox] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        cls, xc, yc, w, h = parts
        items.append(YoloBox(int(cls), float(xc), float(yc), float(w), float(h)))
    return items


def write_yolo_label_file(path: Path, boxes: Iterable[YoloBox]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{box.class_id} {box.x_center:.6f} {box.y_center:.6f} {box.width:.6f} {box.height:.6f}"
        for box in boxes
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def yolo_to_pixel(box: YoloBox, image_w: int, image_h: int) -> PixelBox:
    cx = box.x_center * image_w
    cy = box.y_center * image_h
    w = box.width * image_w
    h = box.height * image_h
    return PixelBox(
        class_id=box.class_id,
        x1=cx - w / 2.0,
        y1=cy - h / 2.0,
        x2=cx + w / 2.0,
        y2=cy + h / 2.0,
    )


def pixel_to_yolo(box: PixelBox, image_w: int, image_h: int) -> YoloBox:
    x1, x2 = sorted((box.x1, box.x2))
    y1, y2 = sorted((box.y1, box.y2))
    w = max(0.0, x2 - x1)
    h = max(0.0, y2 - y1)
    cx = x1 + w / 2.0
    cy = y1 + h / 2.0
    return YoloBox(
        class_id=box.class_id,
        x_center=cx / max(image_w, 1),
        y_center=cy / max(image_h, 1),
        width=w / max(image_w, 1),
        height=h / max(image_h, 1),
    ).clamp()
