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


def test_role_button_disabled_rendering():
    from PySide6.QtWidgets import QApplication, QPushButton

    app = QApplication.instance() or QApplication([])
    def fill(button):
        app.processEvents()
        image = button.grab().toImage()
        return image.pixelColor(image.width() // 2, image.height() // 2).name().lower()

    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            for role, token, flag in (
                ("primary", "success", None),
                ("secondary", "bg_panel_lift", None),
                ("amber", "warning", None),
                ("danger", "danger", None),
                ("nextStep", "success", None),
                ("nextStep", "success_hover", "pulse"),
                ("nextStep", "success_hover", "spotlight"),
            ):
                button = QPushButton()
                button.setProperty("role", role)
                if flag:
                    button.setProperty(flag, True)
                button.setStyleSheet(build_stylesheet())
                button.resize(160, 50)
                button.show()
                try:
                    # No text in the probe, so center pixel samples the fill.
                    # Enabled hover may differ by platform; disabled must not.
                    button.setEnabled(False)
                    assert fill(button) == theme.theme_color("bg_input").lower(), (mode, role, flag)
                    button.setEnabled(True)
                    assert fill(button) != theme.theme_color("bg_input").lower(), (mode, role, flag)
                    button.setEnabled(False)
                    assert fill(button) == theme.theme_color("bg_input").lower(), (mode, role, flag)
                finally:
                    button.close()
    finally:
        theme.set_theme("dark")
