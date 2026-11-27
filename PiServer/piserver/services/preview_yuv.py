"""Validated Picamera2 planar YUV420 preview layout; no hardware ownership."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Mapping


@dataclass(frozen=True)
class YUV420Layout:
    width: int
    height: int
    stride: int

    @classmethod
    def from_config(cls, config: Mapping, requested: tuple[int, int]):
        if config.get("format") != "YUV420":
            raise ValueError("Expected configured YUV420 format")
        size = config.get("size")
        stride = config.get("stride")
        if not isinstance(size, (tuple, list)) or len(size) != 2:
            raise ValueError("Missing configured lores size")
        if any(isinstance(x, bool) or not isinstance(x, Integral) for x in (*size, stride)):
            raise ValueError("Invalid configured lores geometry")
        w, h = map(int, size)
        stride = int(stride)
        if (w, h) != requested or min(w, h) < 2 or w % 2 or h % 2:
            raise ValueError("Configured lores size differs from requested even geometry")
        if stride < w or stride % 2 or stride > 4096:
            raise ValueError("Invalid configured lores stride")
        return cls(w, h, stride)

    def decode_bgr(self, plane, np, cv2):
        """Decode physical planar stride, then crop only padding, not chroma data."""
        data = np.asarray(plane)
        if (data.dtype != np.uint8 or data.shape != (self.height * 3 // 2, self.stride)
                or not data.flags.c_contiguous):
            raise ValueError("Unexpected YUV420 buffer shape, dtype or contiguity")
        # Picamera2 returns packed planes at the configured physical stride.
        # Treat the padded columns as pixels during conversion, then crop the
        # owned RGB/BGR result. Cropping the input matrix would corrupt U/V.
        bgr = cv2.cvtColor(data, cv2.COLOR_YUV2BGR_I420)
        return bgr[:, :self.width]
