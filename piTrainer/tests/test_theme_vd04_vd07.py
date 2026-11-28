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

def test_secondary_button_pressed_rendering():
    from PySide6.QtWidgets import QApplication, QPushButton

    app = QApplication.instance() or QApplication([])
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            button = QPushButton()
            button.setProperty("role", "secondary")
            button.setStyleSheet(build_stylesheet())
            button.resize(160, 50)
            clicks = []
            button.clicked.connect(lambda: clicks.append(True))
            button.show()

            def fill():
                app.processEvents()
                image = button.grab().toImage()
                return image.pixelColor(image.width() // 2, image.height() // 2).name().lower()

            try:
                size = button.size()
                assert fill() in {theme.theme_color("bg_panel_lift").lower(),
                                  theme.theme_color("bg_overlay").lower()}
                button.setDown(True)
                assert fill() == theme.theme_color("bg_input_alt").lower(), mode
                assert button.size() == size
                button.setDown(False)
                assert fill() != theme.theme_color("bg_input_alt").lower(), mode
                button.setEnabled(False)
                assert fill() == theme.theme_color("bg_input").lower(), mode
                assert not clicks
            finally:
                button.close()
    finally:
        theme.set_theme("dark")

def test_local_typography_registration_and_fallback(tmp_path):
    from PySide6.QtGui import QFont, QFontInfo, QRawFont
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    from piTrainer.ui.typography import apply_local_typography, technical_font_stack

    app = QApplication.instance() or QApplication([])
    original = QFont(app.font())
    editor = None
    try:
        fallback = apply_local_typography(app, tmp_path)
        assert not fallback["ui"]["family"] and not fallback["mono"]["family"]
        assert app.font().family() == original.family()
        assert technical_font_stack() == "Consolas, 'Cascadia Mono', monospace"
        actual = apply_local_typography(app)
        assert actual["ui"]["family"].startswith("Inter")
        assert actual["mono"]["family"].startswith("IBM Plex Mono")
        assert actual["ui"]["bytes"] == 879708
        assert actual["mono"]["bytes"] == 173052
        assert app.font().pointSizeF() == original.pointSizeF()
        assert app.font().pixelSize() == original.pixelSize()
        assert QFontInfo(app.font()).family().startswith("Inter")
        editor = QPlainTextEdit("0123456789")
        editor.setStyleSheet(build_stylesheet())
        editor.show()
        app.processEvents()
        assert QFontInfo(editor.font()).family().startswith("IBM Plex Mono")
        for font in (app.font(), editor.font()):
            raw = QRawFont.fromFont(font)
            assert raw.isValid() and all(raw.glyphIndexesForString("Data0123456789"))
    finally:
        if editor is not None:
            editor.close()
        apply_local_typography(app, tmp_path)
        app.setFont(original)


def test_native_form_keyboard_and_disabled_state():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit, QSlider, QSpinBox, QVBoxLayout, QWidget

    app = QApplication.instance() or QApplication([])
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            root = QWidget()
            layout = QVBoxLayout(root)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 10)
            slider.setValue(4)
            check = QCheckBox("Toggle")
            combo = QComboBox()
            combo.addItems(["First", "Second"])
            spin = QSpinBox()
            spin.setValue(5)
            edit = QLineEdit("Preserved")
            widgets = (slider, check, combo, spin, edit)
            for widget in widgets:
                layout.addWidget(widget)
            root.setStyleSheet(build_stylesheet())
            root.resize(320, 300)
            root.show()
            try:
                app.processEvents()
                QTest.keyClick(slider, Qt.Key.Key_Right)
                assert slider.value() == 5
                QTest.keyClick(check, Qt.Key.Key_Space)
                assert check.isChecked()
                QTest.keyClick(combo, Qt.Key.Key_Down)
                assert combo.currentIndex() == 1
                QTest.keyClick(spin, Qt.Key.Key_Up)
                assert spin.value() == 6
                before = [widget.size() for widget in widgets]
                for widget in widgets:
                    widget.setEnabled(False)
                app.processEvents()
                assert [widget.size() for widget in widgets] == before
                assert slider.value() == 5 and check.isChecked()
                assert combo.currentIndex() == 1 and spin.value() == 6
                assert edit.text() == "Preserved"
                for widget in widgets:
                    widget.setEnabled(True)
                app.processEvents()
                assert [widget.size() for widget in widgets] == before
                QTest.keyClick(check, Qt.Key.Key_Space)
                assert not check.isChecked()
            finally:
                root.close()
    finally:
        theme.set_theme("dark")


def test_native_tab_interaction_and_disabled_selection():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QTabWidget, QWidget

    app = QApplication.instance() or QApplication([])
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            tabs = QTabWidget()
            tabs.setObjectName("mainWorkflowTabs")
            for title in ("Data", "Preprocess", "Train"):
                tabs.addTab(QWidget(), title)
            tabs.setStyleSheet(build_stylesheet())
            tabs.resize(600, 220)
            tabs.show()
            try:
                bar = tabs.tabBar()
                bar.setFocus(Qt.FocusReason.TabFocusReason)
                app.processEvents()
                before = [bar.tabRect(i).size() for i in range(3)]
                tabs.setTabEnabled(1, False)
                QTest.keyClick(bar, Qt.Key.Key_Right)
                assert tabs.currentIndex() == 2
                assert not tabs.isTabEnabled(1)
                QTest.keyClick(bar, Qt.Key.Key_Left)
                assert tabs.currentIndex() == 0
                tabs.setTabEnabled(1, True)
                QTest.keyClick(bar, Qt.Key.Key_Right)
                assert tabs.currentIndex() == 1
                app.processEvents()
                assert [bar.tabRect(i).size() for i in range(3)] == before
            finally:
                tabs.close()
    finally:
        theme.set_theme("dark")


def test_flat_form_group_preserves_children_and_title():
    from PySide6.QtWidgets import QApplication, QFrame, QGroupBox, QLineEdit, QVBoxLayout

    app = QApplication.instance() or QApplication([])
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            panel = QFrame()
            panel.setProperty("role", "splitterPanel")
            layout = QVBoxLayout(panel)
            group = QGroupBox("Configuration")
            group.setProperty("role", "formGroup")
            layout.addWidget(group)
            fields = QVBoxLayout(group)
            field = QLineEdit("Keep this value")
            fields.addWidget(field)
            panel.setStyleSheet(build_stylesheet())
            panel.resize(400, 180)
            panel.show()
            try:
                app.processEvents()
                assert group.title() == "Configuration"
                assert field.isVisible() and field.isEnabled()
                assert field.geometry().width() > 0
                assert field.text() == "Keep this value"
                field.setFocus()
                app.processEvents()
                assert field.text() == "Keep this value"
                assert group.isAncestorOf(field)
            finally:
                panel.close()
    finally:
        theme.set_theme("dark")


def test_content_tabs_flat_pane_preserves_navigation_and_editor():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLineEdit, QTabWidget, QVBoxLayout, QWidget

    app = QApplication.instance() or QApplication([])
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            tabs = QTabWidget()
            tabs.setProperty("role", "contentTabs")
            first, second = QWidget(), QWidget()
            edit = QLineEdit("unchanged")
            QVBoxLayout(first).addWidget(edit)
            tabs.addTab(first, "Details")
            tabs.addTab(second, "Preview")
            tabs.setStyleSheet(build_stylesheet())
            tabs.resize(500, 220)
            tabs.show()
            try:
                app.processEvents()
                assert edit.isVisible() and edit.isEnabled()
                bar = tabs.tabBar()
                before = [bar.tabRect(i).size() for i in range(2)]
                bar.setFocus(Qt.FocusReason.TabFocusReason)
                QTest.keyClick(bar, Qt.Key.Key_Right)
                assert tabs.currentIndex() == 1
                QTest.keyClick(bar, Qt.Key.Key_Left)
                assert tabs.currentIndex() == 0
                app.processEvents()
                assert edit.isVisible() and edit.text() == "unchanged"
                assert [bar.tabRect(i).size() for i in range(2)] == before
            finally:
                tabs.close()
    finally:
        theme.set_theme("dark")


def test_density_chrome_tokens_preserve_action_minimums():
    from piTrainer.ui.formatting import get_density_profile, stylesheet_tokens

    for mode, table_pad, toolbar_pad, toolbar_gap in (
        ("compact", 3, 4, 6), ("comfortable", 5, 6, 8), ("spacious", 6, 8, 10),
    ):
        tokens = stylesheet_tokens(mode)
        css = build_stylesheet(mode)
        profile = get_density_profile(mode)
        assert tokens["TABLE_CELL_PAD"] == str(table_pad)
        assert tokens["TOOLBAR_PAD"] == str(toolbar_pad)
        assert tokens["TOOLBAR_GAP"] == str(toolbar_gap)
        assert f"padding: {table_pad}px;" in css
        assert f"min-height: {profile.button_min}px;" in css
        assert f"min-height: {profile.input_min}px;" in css
        assert "@TABLE_CELL_PAD@" not in css
        assert "@TOOLBAR_PAD@" not in css


def test_shared_plot_style_retains_series_and_theme():
    import pandas as pd
    from matplotlib.figure import Figure
    from matplotlib.colors import to_rgba
    from piTrainer.services.data.plot_service import render_plot
    from piTrainer.services.validation.validation_plot import render_validation_plot

    df = pd.DataFrame({"steering": [-.5, .25, .75], "throttle": [.2, .4, .6]})
    result = {"steering_true": [-.5, .25, .75], "throttle_true": [.2, .4, .6],
              "steering_pred": [-.4, .2, .7], "throttle_pred": [.1, .4, .5],
              "steering_error": [.1, -.05, -.05], "throttle_error": [-.1, 0, -.1]}
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            ax = Figure().add_subplot(111)
            render_plot(ax, df, "Steering + Speed Timeline", "All loaded sessions")
            assert list(ax.lines[0].get_ydata()) == list(df.steering)
            assert list(ax.lines[1].get_ydata()) == list(df.throttle)
            assert ax.lines[0].get_linestyle() != ax.lines[1].get_linestyle()
            assert ax.get_facecolor() == to_rgba(theme.theme_color("plot_axis"))
            assert ax.figure.get_facecolor() == to_rgba(theme.theme_color("plot_bg"))
            ax = Figure().add_subplot(111)
            render_validation_plot(ax, result, "Sample Prediction Trace")
            assert len(ax.lines) == 4
            assert list(ax.lines[1].get_ydata()) == result["steering_pred"]
            assert list(ax.lines[3].get_ydata()) == result["throttle_pred"]
            assert ax.lines[0].get_linestyle() != ax.lines[1].get_linestyle()
            assert ax.lines[2].get_linestyle() != ax.lines[3].get_linestyle()
            assert ax.get_legend().get_texts()[0].get_color() == theme.theme_color("text_primary")
    finally:
        theme.set_theme("dark")


def test_numeric_table_alignment_preserves_display_and_selection():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
    from piTrainer.ui.typography import align_numeric_table_item

    app = QApplication.instance() or QApplication([])
    table = QTableWidget(1, 2)
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            table.setStyleSheet(build_stylesheet())
            value = QTableWidgetItem("5.960e-08")
            value.setToolTip(value.text())
            align_numeric_table_item(value)
            table.setItem(0, 0, value)
            table.setItem(0, 1, QTableWidgetItem("Unknown"))
            table.setCurrentCell(0, 0)
            assert value.text() == "5.960e-08"
            assert value.toolTip() == value.text()
            assert value.textAlignment() & Qt.AlignmentFlag.AlignRight
            assert table.currentItem() is value
            assert table.item(0, 1).text() == "Unknown"
    finally:
        table.close()
        theme.set_theme("dark")


def test_accessible_table_keyboard_focus_preserves_selection():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

    app = QApplication.instance() or QApplication([])
    try:
        for mode in ("dark", "light"):
            theme.set_theme(mode)
            window = QWidget()
            layout = QVBoxLayout(window)
            table = QTableWidget(2, 1)
            table.setAccessibleName("Fixture comparison records")
            table.setItem(0, 0, QTableWidgetItem("0.125"))
            table.setItem(1, 0, QTableWidgetItem("0.250"))
            editor = QLineEdit("unchanged")
            layout.addWidget(table)
            layout.addWidget(editor)
            QWidget.setTabOrder(table, editor)
            window.setStyleSheet(build_stylesheet("compact"))
            window.resize(360, 260)
            window.show()
            window.activateWindow()
            try:
                app.processEvents()
                table.setCurrentCell(0, 0)
                table.setFocus(Qt.FocusReason.TabFocusReason)
                app.processEvents()
                assert table.hasFocus()
                before = table.size()
                QTest.keyClick(table, Qt.Key.Key_Down)
                assert table.currentRow() == 1
                assert table.currentItem().text() == "0.250"
                assert table.size() == before
                # Ctrl+Tab traverses out of Qt item views even when Tab edits cells.
                QTest.keyClick(table, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
                app.processEvents()
                assert editor.hasFocus()
                assert editor.text() == "unchanged"
                assert table.item(0, 0).text() == "0.125"
                assert table.accessibleName() == "Fixture comparison records"
            finally:
                window.close()
    finally:
        theme.set_theme("dark")
