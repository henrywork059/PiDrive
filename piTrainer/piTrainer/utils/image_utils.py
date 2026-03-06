from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap



def load_scaled_pixmap(path: str, width: int, height: int):
    if not path:
        return None
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
