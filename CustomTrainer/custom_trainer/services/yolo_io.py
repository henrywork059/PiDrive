from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class YoloBox:
    class_id: int
    xc: float
    yc: float
    w: float
    h: float


@dataclass
class PixelBox:
    class_id: int
    x1: float
    y1: float
    x2: float
    y2: float


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def read_yolo_label_file(path: Path) -> list[YoloBox]:
    if not path.exists():
        return []
    boxes: list[YoloBox] = []
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        try:
            class_id = int(float(parts[0]))
            xc, yc, w, h = (float(parts[i]) for i in range(1, 5))
        except ValueError:
            continue
        boxes.append(YoloBox(class_id=class_id, xc=clamp01(xc), yc=clamp01(yc), w=clamp01(w), h=clamp01(h)))
    return boxes


def write_yolo_label_file(path: Path, boxes: list[YoloBox]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'{int(box.class_id)} {box.xc:.6f} {box.yc:.6f} {box.w:.6f} {box.h:.6f}'
        for box in boxes
        if box.w > 0 and box.h > 0
    ]
    content = '\n'.join(lines)
    if content:
        content += '\n'
    path.write_text(content, encoding='utf-8')


def yolo_to_pixel(box: YoloBox, image_width: int, image_height: int) -> PixelBox:
    x1 = (box.xc - box.w / 2.0) * image_width
    y1 = (box.yc - box.h / 2.0) * image_height
    x2 = (box.xc + box.w / 2.0) * image_width
    y2 = (box.yc + box.h / 2.0) * image_height
    return PixelBox(class_id=box.class_id, x1=x1, y1=y1, x2=x2, y2=y2)


def pixel_to_yolo(box: PixelBox, image_width: int, image_height: int) -> YoloBox:
    x1, x2 = sorted((float(box.x1), float(box.x2)))
    y1, y2 = sorted((float(box.y1), float(box.y2)))
    w = max(0.0, x2 - x1)
    h = max(0.0, y2 - y1)
    xc = x1 + w / 2.0
    yc = y1 + h / 2.0
    return YoloBox(
        class_id=int(box.class_id),
        xc=clamp01(xc / max(image_width, 1)),
        yc=clamp01(yc / max(image_height, 1)),
        w=clamp01(w / max(image_width, 1)),
        h=clamp01(h / max(image_height, 1)),
    )
