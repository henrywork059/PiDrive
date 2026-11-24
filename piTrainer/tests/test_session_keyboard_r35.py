"""Native offscreen Qt tests for actual Data session controls (no user settings)."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from piTrainer.app_state import AppState
from piTrainer.panels.data.session_source_panel import SessionSourcePanel
from piTrainer.ui.styles import build_stylesheet


class SessionKeyboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = QSettings(str(Path(self.tmp.name) / "settings.ini"), QSettings.IniFormat)
        self.state = AppState()
        self.state.records_root = self.tmp.name
        self.panel = self.make_panel()
        self.addCleanup(self.panel.close)

    def make_panel(self):
        from unittest.mock import patch
        with patch.object(SessionSourcePanel, "_settings", lambda _: self.settings):
            panel = SessionSourcePanel(self.state, lambda: None, lambda: None)
        # Keep later writes in the same disposable INI file too.
        panel._settings = lambda: self.settings
        panel.set_sessions(["fixture-a", "fixture-b"])
        panel.show()
        self.app.processEvents()
        return panel

    def test_keyboard_selects_exact_named_session(self):
        self.assertEqual(self.panel.path_edit.accessibleName(), "Records root folder")
        first, second = self.panel._rows
        self.assertEqual(first.checkbox.accessibleName(), "Select session fixture-a")
        self.assertEqual(second.checkbox.accessibleName(), "Select session fixture-b")
        second.checkbox.setFocus()
        QTest.keyClick(second.checkbox, Qt.Key_Space)
        self.assertEqual(self.panel.selected_sessions(), ["fixture-b"])
        QTest.keyClick(second.checkbox, Qt.Key_Space)
        self.assertEqual(self.panel.selected_sessions(), [])

    def test_keyboard_resize_clamp_persist_and_reset(self):
        handle = self.panel.resize_handle
        self.assertEqual(handle.focusPolicy(), Qt.StrongFocus)
        self.assertEqual(handle.accessibleName(), "Session list height")
        handle.setFocus()
        start = self.panel._current_session_list_height()
        QTest.keyClick(handle, Qt.Key_Down)
        self.assertEqual(self.panel._current_session_list_height(), start + 20)
        self.settings.sync()
        restored = self.make_panel()
        self.addCleanup(restored.close)
        self.assertEqual(restored._current_session_list_height(), start + 20)
        self.panel._set_session_list_height(900)
        QTest.keyClick(handle, Qt.Key_Down)
        self.assertEqual(self.panel._current_session_list_height(), 900)
        QTest.keyClick(handle, Qt.Key_Home)
        self.assertEqual(self.panel._current_session_list_height(), 260)

    def test_focus_style_available_in_all_profiles(self):
        for profile in ("compact", "comfortable", "spacious"):
            css = build_stylesheet(profile)
            self.assertIn("QFrame#sessionListResizeHandle:focus", css)
            self.assertIn("QPushButton[role]:focus", css)
            self.assertNotIn("@COLOR_INFO@", css)


if __name__ == "__main__":
    unittest.main()
