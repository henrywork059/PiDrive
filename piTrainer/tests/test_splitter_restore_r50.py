"""Native Qt layout regression using the real DockPage and a disposable INI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel
from piTrainer.pages.dock_page import DockPage


class SplitterRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_page(self):
        page = DockPage("r50_fixture")
        splitter = page.make_horizontal_splitter(
            [QLabel("Data"), QLabel("Review"), QLabel("Preview")],
            sizes=[200, 500, 300], minimums=[0, 0, 0],
            object_name="workspace",
        )
        page.set_workspace_widget(splitter)
        screen = self.app.primaryScreen().availableGeometry()
        page.resize(min(740, screen.width() - 40), min(600, screen.height() - 60))
        page.show()
        self.addCleanup(page.close)
        self.app.processEvents()
        return page, splitter

    def test_panel_navigation_preserves_saved_splitter_proportions(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(str(Path(tmp) / "layout.ini"), QSettings.IniFormat)
            with patch("piTrainer.pages.dock_page.QSettings", return_value=settings):
                page = DockPage("r50_navigation_fixture")
                frames = [page.make_panel_frame(str(i), title, QLabel(title))
                          for i, title in enumerate(("Input", "Review", "Output"))]
                splitter = page.make_horizontal_splitter(frames, sizes=[200, 300, 200],
                    minimums=[0, 0, 0], object_name="workspace")
                page.set_workspace_widget(splitter)
                page.resize(740, 500)
                page.show()
                self.addCleanup(page.close)
                page.activateWindow()
                self.app.processEvents()
                splitter.setSizes([220, 260, 220])
                splitter.capture_current_ratios()
                page.save_layout()
                settings.sync()
                keys = {key: settings.value(key) for key in settings.allKeys()}
                before = list(splitter.sizes())
                self.assertEqual(page.workspace_panel_titles(), ("Input", "Review", "Output"))
                self.assertTrue(page.focus_workspace_panel(1))
                self.assertTrue(page.cycle_workspace_panel(1))
                self.assertEqual(self.app.focusWidget().accessibleName(), "Output panel")
                self.assertTrue(page.cycle_workspace_panel(-1))
                self.assertEqual(self.app.focusWidget().accessibleName(), "Review panel")
                self.assertFalse(page.focus_workspace_panel(-1))
                self.assertEqual(splitter.sizes(), before)
                self.assertEqual({key: settings.value(key) for key in settings.allKeys()}, keys)

    def test_save_restore_and_resize_keep_visible_user_proportions(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(str(Path(tmp) / "layout.ini"), QSettings.IniFormat)
            with patch("piTrainer.pages.dock_page.QSettings", return_value=settings):
                first, source = self.make_page()
                source.setSizes([400, 200, 400])
                source.capture_current_ratios()
                first.save_layout()
                settings.sync()
                second, restored = self.make_page()
                second.restore_layout()
                self.app.processEvents()
                # Qt may constrain window geometry to the available display.
                # Test the saved proportions, not screen-dependent pixel sizes.
                saved_sizes = source.sizes()
                proportions = [n / sum(saved_sizes) for n in saved_sizes]
                self.assertAlmostEqual(proportions[0], 0.4, delta=0.025)
                self.assertAlmostEqual(proportions[1], 0.2, delta=0.025)
                restored_sizes = restored.sizes()
                self.assertTrue(all(n > 0 for n in restored_sizes))
                for expected, actual in zip(proportions, [n / sum(restored_sizes) for n in restored_sizes]):
                    self.assertAlmostEqual(expected, actual, delta=0.025,
                                           msg=f"saved={saved_sizes}, restored={restored_sizes}")
                second.resize(second.width() + 200, second.height() + 50)
                self.app.processEvents()
                sizes = restored.sizes()
                self.assertTrue(all(n > 0 for n in sizes))
                for expected, actual in zip(proportions, [n / sum(sizes) for n in sizes]):
                    self.assertAlmostEqual(expected, actual, delta=0.035)
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()
