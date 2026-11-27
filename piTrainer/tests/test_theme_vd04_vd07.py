from PySide6.QtCore import QSettings
from piTrainer.ui import theme
from piTrainer.ui.styles import build_stylesheet

def test_theme_roles_and_settings(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "appearance.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(theme, "appearance_settings", lambda: settings)
    settings.setValue("unrelated", "preserve")
    identity = id(theme.THEME_COLORS)
    try:
        assert theme.saved_theme() == "dark"
        dark = dict(theme.THEME_COLORS)
        assert dark["bg_app"] == "#14171C"
        assert theme.save_theme("light")
        assert theme.saved_theme() == "light"
        assert theme.set_theme(theme.saved_theme()) == "light"
        assert id(theme.THEME_COLORS) == identity
        assert set(theme.THEME_COLORS) == set(dark)
        assert theme.theme_color("bg_app") == "#F4F6FA"
        assert "#F4F6FA" in build_stylesheet()
        assert settings.value("unrelated") == "preserve"
        assert not theme.save_theme("invalid")
        assert theme.saved_theme() == "light"
        assert theme.set_theme("invalid") == "dark"
        assert theme.THEME_COLORS == dark
    finally:
        theme.set_theme("dark")
