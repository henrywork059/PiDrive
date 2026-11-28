"""Register component-local fonts, retaining native fallback and sizing."""
from pathlib import Path

_FONT_ROOT = Path(__file__).resolve().with_name("fonts")
_MONO_FAMILY = None
_FALLBACK_MONO = "Consolas, 'Cascadia Mono', monospace"


def apply_local_typography(app, font_dir=None):
    """Return actual registration families/byte counts. No remote downloads."""
    from PySide6.QtGui import QFont, QFontDatabase

    global _MONO_FAMILY
    root = Path(font_dir) if font_dir is not None else _FONT_ROOT
    report = {}
    for key, filename, prefix in (
        ("ui", "InterVariable.ttf", "Inter"),
        ("mono", "IBMPlexMono-Regular.ttf", "IBM Plex Mono"),
    ):
        path = root / filename
        try:
            size = path.stat().st_size
            font_id = QFontDatabase.addApplicationFont(str(path))
            families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            family = next((item for item in families if item.startswith(prefix)), None)
        except (OSError, RuntimeError):
            size, family = 0, None
        report[key] = {"family": family, "bytes": size}
    family = report["ui"]["family"]
    if family:
        font = QFont(app.font())
        font.setFamily(family)
        app.setFont(font)
    _MONO_FAMILY = report["mono"]["family"]
    return report


def technical_font_stack():
    if _MONO_FAMILY:
        return '"' + _MONO_FAMILY + '", ' + _FALLBACK_MONO
    return _FALLBACK_MONO
