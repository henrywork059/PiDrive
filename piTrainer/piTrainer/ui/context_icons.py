"""Original 24-unit outline icons; no network, font or extra assets needed."""
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from .theme import theme_color

_GLYPHS = {
    "refresh": '<path d="M20 9a8 8 0 1 0 .2 6M20 4v5h-5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/>',
    "compare": '<path d="M5 7h14m-4-4 4 4-4 4M19 17H5m4-4-4 4 4 4"/>',
}


def contextual_icon(name):
    """Render matching theme-colored glyphs at native and scaled resolutions."""
    glyph = _GLYPHS[name]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           'fill="none" stroke="' + theme_color("text_primary") +
           '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
           + glyph + '</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    icon = QIcon()
    for scale in (1, 2, 3):
        pixmap = QPixmap(16 * scale, 16 * scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        icon.addPixmap(pixmap)
    return icon


def set_context_icon(button, name):
    """Keep native text, tooltip, accessible name, action and focus."""
    button.setIcon(contextual_icon(name))
    button.setIconSize(QSize(16, 16))
