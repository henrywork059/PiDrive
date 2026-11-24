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
        page.resize(1000, 650)
        page.show()
        self.addCleanup(page.close)
        self.app.processEvents()
        return page, splitter

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
                for a, b in zip(source.sizes(), restored.sizes()):
                    self.assertLessEqual(abs(a - b), 12)
                proportions = [n / sum(restored.sizes()) for n in restored.sizes()]
                second.resize(1320, 750)
                self.app.processEvents()
                sizes = restored.sizes()
                self.assertTrue(all(n > 0 for n in sizes))
                for expected, actual in zip(proportions, [n / sum(sizes) for n in sizes]):
                    self.assertAlmostEqual(expected, actual, delta=0.035)
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()
