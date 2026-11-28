"""Bounded, workspace-only replay for the existing virtual camera adapter."""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image, ImageEnhance

MAX_FRAMES = 10000
MAX_IMAGE_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 4096 * 4096
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
VIDEO_SUFFIXES = {".avi", ".mp4", ".mov", ".mkv"}
MAX_VIDEO_BYTES = 512 * 1024 * 1024

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
        frame = transform_image(image, settings)
        self.index += 1
        self.delivered += 1
        return frame


def transform_image(image, settings):
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
    return frame


class VideoReplay:
    """Sequential decode; never treat a filename as a URL or camera device."""
    def __init__(self, workspace, source, loop=False):
        import cv2
        if type(loop) is not bool:
            raise ValueError("loop must be a boolean.")
        relative = Path(source)
        if (relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2
                or relative.parts[0] != "replay" or relative.suffix.lower() not in VIDEO_SUFFIXES):
            raise ValueError("Use a local video under replay/ with a supported extension.")
        self.root = contained(workspace, Path(workspace) / "replay")
        self.path = contained(self.root, Path(workspace) / relative)
        self.source = relative.as_posix()
        self.loop = loop
        self.index = self.delivered = 0
        self.capture = None
        self.frame_count = 0
        self.source_fps = 0.0
        try:
            self._open()
        finally:
            self.close()

    def _open(self):
        import cv2
        self.close()
        path = contained(self.root, self.path)
        if not path.is_file() or path.stat().st_size > MAX_VIDEO_BYTES:
            raise ValueError("Replay video is missing or exceeds the 512 MiB size limit.")
        capture = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
        try:
            if not capture.isOpened():
                raise ValueError("Replay video cannot be opened by the local decoder.")
            raw_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = capture.get(cv2.CAP_PROP_FPS)
            if (not all(math.isfinite(v) for v in (raw_count, width, height, fps))
                    or not 1 <= raw_count <= MAX_FRAMES
                    or width <= 0 or height <= 0 or width * height > MAX_PIXELS
                    or fps <= 0):
                raise ValueError("Video needs bounded, known frame count, geometry and frame rate.")
            count = int(raw_count)
            if self.frame_count and count != self.frame_count:
                raise ValueError("Replay video frame count changed after selection.")
            self.frame_count = count
            self.source_fps = fps
            self.capture = capture
        except Exception:
            capture.release()
            raise

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def reset(self):
        self.close()
        self.index = self.delivered = 0

    def status(self):
        return {"mode": "replay", "media": "video", "source": self.source,
                "frame_count": self.frame_count, "next_index": self.index,
                "delivered": self.delivered, "loop": self.loop, "source_fps": self.source_fps,
                "exhausted": self.index >= self.frame_count}

    def render(self, settings):
        import cv2
        if self.index >= self.frame_count:
            self.close()
            if not self.loop:
                raise RuntimeError("Replay exhausted; no new camera frame.")
            self.index = 0
        if self.capture is None:
            if self.index:
                raise RuntimeError("Replay decoder closed mid-stream; restart runtime to retry.")
            self._open()
        ok, bgr = self.capture.read()
        if not ok or bgr is None or bgr.ndim != 3 or bgr.shape[2] != 3 or bgr.shape[0] * bgr.shape[1] > MAX_PIXELS:
            self.close()
            raise RuntimeError("Replay video decode failed before expected end.")
        try:
            frame = transform_image(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), settings)
        except Exception:
            self.close()
            raise
        self.index += 1
        self.delivered += 1
        return frame


def open_replay(workspace, source, loop=False):
    if not isinstance(source, str) or not source.strip() or len(source) > 512:
        raise ValueError("Supply a workspace-relative recording, image folder or video.")
    relative = Path(source)
    if relative.suffix.lower() in VIDEO_SUFFIXES:
        return VideoReplay(workspace, source, loop)
    return ImageReplay(workspace, source, loop)
