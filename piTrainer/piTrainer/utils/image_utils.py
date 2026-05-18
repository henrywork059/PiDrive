from __future__ import annotations

from collections import OrderedDict

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


_PIXMAP_CACHE: OrderedDict[str, QPixmap] = OrderedDict()
_MAX_CACHE_ITEMS = 96


def load_scaled_pixmap(path: str, width: int, height: int):
    if not path:
        return None
    cache_key = f"{path}::{int(width)}x{int(height)}"
    cached = _PIXMAP_CACHE.get(cache_key)
    if cached is not None and not cached.isNull():
        _PIXMAP_CACHE.move_to_end(cache_key)
        return cached
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    scaled = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    _PIXMAP_CACHE[cache_key] = scaled
    _PIXMAP_CACHE.move_to_end(cache_key)
    while len(_PIXMAP_CACHE) > _MAX_CACHE_ITEMS:
        _PIXMAP_CACHE.popitem(last=False)
    return scaled
