from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QTransform


# R38: cache ONLY unannotated scaled previews. QPainter overlays copy/detach
# the returned QPixmap and are never cached, so labels remain frame-specific.
# The previous 96-item-only bound could retain hundreds of MiB at large window
# sizes. Both item and estimated decoded-pixel budgets must now be respected.
_PIXMAP_CACHE: OrderedDict[tuple[str, int, int, bool, int, int], QPixmap] = OrderedDict()
_MAX_CACHE_ITEMS = 96
_MAX_CACHE_BYTES = 64 * 1024 * 1024
_PIXMAP_CACHE_BYTES = 0


def _estimated_pixmap_bytes(pixmap: QPixmap) -> int:
    """Conservative decoded image size; never claim this is process RSS."""
    if pixmap.isNull():
        return 0
    # Qt pixmaps can use a platform-specific backing store. Estimate at least
    # RGBA8888 (4 bytes/pixel), so memory use is bounded by a practical budget
    # rather than by item count alone. Actual GPU/driver allocations may vary.
    bytes_per_pixel = max(4, (int(pixmap.depth()) + 7) // 8)
    return int(pixmap.width()) * int(pixmap.height()) * bytes_per_pixel


def _evict_to_budget() -> None:
    global _PIXMAP_CACHE_BYTES
    while len(_PIXMAP_CACHE) > _MAX_CACHE_ITEMS or _PIXMAP_CACHE_BYTES > _MAX_CACHE_BYTES:
        _key, old = _PIXMAP_CACHE.popitem(last=False)
        _PIXMAP_CACHE_BYTES -= _estimated_pixmap_bytes(old)
    _PIXMAP_CACHE_BYTES = max(0, _PIXMAP_CACHE_BYTES)


def clear_scaled_pixmap_cache() -> None:
    """Release scaled images when a source dataset is changed or removed."""
    global _PIXMAP_CACHE_BYTES
    _PIXMAP_CACHE.clear()
    _PIXMAP_CACHE_BYTES = 0


def scaled_pixmap_cache_stats() -> dict[str, int]:
    """Observability for tests/benchmarks; not a memory allocator measurement."""
    return {
        'items': len(_PIXMAP_CACHE),
        'estimated_bytes': _PIXMAP_CACHE_BYTES,
        'max_items': _MAX_CACHE_ITEMS,
        'max_bytes': _MAX_CACHE_BYTES,
    }


def load_scaled_pixmap(path: str, width: int, height: int, flip_lr: bool = False):
    """Load a source image and keep only a bounded, unannotated scaled copy.

    A source-file mtime+size signature avoids reusing an old cached image when
    a recorder or an external editor replaces a frame at the same filename.
    QPixmap work stays on the Qt GUI thread, just as it did before R38.
    """
    global _PIXMAP_CACHE_BYTES
    if not path:
        return None
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    width, height = int(width), int(height)
    cache_key = (path, width, height, bool(flip_lr), stat.st_mtime_ns, stat.st_size)
    cached = _PIXMAP_CACHE.get(cache_key)
    if cached is not None and not cached.isNull():
        _PIXMAP_CACHE.move_to_end(cache_key)
        return cached
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    if flip_lr:
        pixmap = pixmap.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
    scaled = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    cost = _estimated_pixmap_bytes(scaled)
    if cost <= _MAX_CACHE_BYTES and not scaled.isNull():
        # Drop stale signatures of this same source/dimensions on replacement;
        # otherwise each overwrite would accumulate another cached copy.
        stale = [
            key for key in _PIXMAP_CACHE
            if key[:4] == cache_key[:4] and key != cache_key
        ]
        for key in stale:
            _PIXMAP_CACHE_BYTES -= _estimated_pixmap_bytes(_PIXMAP_CACHE.pop(key))
        _PIXMAP_CACHE[cache_key] = scaled
        _PIXMAP_CACHE.move_to_end(cache_key)
        _PIXMAP_CACHE_BYTES += cost
        _evict_to_budget()
    return scaled
