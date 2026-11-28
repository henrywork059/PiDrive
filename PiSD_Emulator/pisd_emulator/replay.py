"""Bounded, workspace-only image replay for the existing virtual camera adapter."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageEnhance

MAX_FRAMES = 10000
MAX_IMAGE_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 4096 * 4096
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

def contained(root, candidate):
    root = Path(root).resolve()
    path = Path(candidate).resolve()
    if path == root or root not in path.parents:
        raise ValueError("Replay path must stay within its designated workspace folder.")
    return path

class ImageReplay:
    def __init__(self, workspace, source, loop=False):
        if not isinstance(source, str) or not source.strip() or len(source) > 512:
            raise ValueError("Supply a workspace-relative recording or replay folder.")
        if type(loop) is not bool:
            raise ValueError("loop must be a boolean.")
        relative = Path(source)
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2 or relative.parts[0] not in {"recordings", "replay"}:
            raise ValueError("Use recordings/<session> or replay/<folder>.")
        root = contained(workspace, Path(workspace) / relative.parts[0])
        folder = contained(root, Path(workspace) / relative)
        if not folder.is_dir():
            raise ValueError("Replay folder does not exist.")
        labels = folder / "labels.jsonl"
        frames = []
        if labels.is_file():
            with contained(folder, labels).open("rb") as handle:
                while True:
                    line = handle.readline(1024 * 1024 + 1)
                    if not line:
                        break
                    if len(line) > 1024 * 1024:
                        raise ValueError("Replay label exceeds size limit.")
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    path = row.get("frame") if isinstance(row, dict) else None
                    if not isinstance(path, str) or Path(path).is_absolute() or ".." in Path(path).parts:
                        raise ValueError("Invalid replay label frame path.")
                    frames.append(contained(folder, folder / path))
                    if len(frames) > MAX_FRAMES:
                        raise ValueError("Replay frame limit exceeded.")
        else:
            for path in folder.iterdir():
                if path.suffix.lower() in IMAGE_SUFFIXES:
                    frames.append(contained(folder, path))
                    if len(frames) > MAX_FRAMES:
                        raise ValueError("Replay frame limit exceeded.")
            frames.sort(key=lambda path: path.name)
        if not frames or any(p.suffix.lower() not in IMAGE_SUFFIXES or not p.is_file() or p.stat().st_size > MAX_IMAGE_BYTES for p in frames):
            raise ValueError("Replay needs valid JPG/PNG frame files within the size limit.")
        self.folder = folder
        self.source = relative.as_posix()
        self.frames = tuple(frames)
        self.loop = loop
        self.index = 0
        self.delivered = 0

    def reset(self):
        self.index = self.delivered = 0

    def status(self):
        return {"mode": "replay", "source": self.source, "frame_count": len(self.frames),
                "next_index": self.index, "delivered": self.delivered, "loop": self.loop,
                "exhausted": self.index >= len(self.frames)}

    def render(self, settings):
        if self.index >= len(self.frames):
            if not self.loop:
                raise RuntimeError("Replay exhausted; no new camera frame.")
            self.index = 0
        path = contained(self.folder, self.frames[self.index])
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError("Replay image exceeds byte limit.")
        with Image.open(path) as original:
            if original.width * original.height > MAX_PIXELS:
                raise ValueError("Replay image exceeds pixel limit.")
            image = original.convert("RGB")
        width = max(64, min(1920, int(settings.width)))
        height = max(48, min(1080, int(settings.height)))
        image = image.resize((width, height), Image.Resampling.BILINEAR)
        image = ImageEnhance.Brightness(image).enhance(max(.1, min(2., 1. + float(settings.brightness) * .5)))
        image = ImageEnhance.Contrast(image).enhance(max(.1, min(2., float(settings.contrast))))
        image = ImageEnhance.Color(image).enhance(max(0., min(2., float(settings.saturation))))
        if settings.hflip:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if settings.vflip:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        frame = np.asarray(image, dtype=np.uint8)[:, :, ::-1].copy()
        self.index += 1
        self.delivered += 1
        return frame
