"""R50 realistic soft-minimum allocation and persistent Qt workspace layout.

Uses actual piTrainer Data/Validate/Train splitter presets, real panel frames,
real QSplitter sizing, and a disposable settings file. No user configuration.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel

from piTrainer.pages.dock_page import DockPage, ResponsiveSplitter
from piTrainer.ui.formatting import splitter_args


class RealisticMinimumSplitterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_page(self, preset: str, page_id: str = "r50_real_minimums"):
        page = DockPage(page_id)
        frames = [
            page.make_panel_frame(name, title, QLabel(title + " content"))
            for name, title in (
                ("workflow_controls", "Workflow"),
                ("record_review", "Records"),
                ("image_preview", "Preview"),
            )
        ]
        splitter = page.make_horizontal_splitter(
            frames, object_name="main_workspace", **splitter_args(preset)
        )
        page.set_workspace_widget(splitter)
        screen = self.app.primaryScreen().availableGeometry()
        narrow = max(480, min(730, screen.width() - 60))
        page.resize(narrow, max(360, min(530, screen.height() - 80)))
        page.show()
        self.addCleanup(page.close)
        self.app.processEvents()
        return page, splitter, frames

    def test_presets_preserve_whole_panel_ratios_when_space_allows(self):
        for name in (
            "three_panel_workspace",
            "validation_three_panel_workspace",
            "train_three_panel_workspace",
        ):
            with self.subTest(preset=name):
                preset = splitter_args(name)
                minimums = preset["minimums"]
                weights = preset["sizes"]
                total = sum(weights)
                proportions = [value / total for value in weights]
                # Actual preset at its intended design width: the whole-pane
                # targets already satisfy all three soft minima.
                self.assertTrue(all(v >= m for v, m in zip(weights, minimums)))
                allocated = ResponsiveSplitter._allocate_preferred_sizes(
                    total, proportions, minimums
                )
                self.assertEqual(allocated, weights)
                self.assertEqual(sum(allocated), total)

    def test_user_custom_ratio_is_respected_and_constrained_only_as_needed(self):
        minimums = splitter_args("three_panel_workspace")["minimums"]
        preferred = [0.5, 0.25, 0.25]
        self.assertEqual(
            ResponsiveSplitter._allocate_preferred_sizes(1200, preferred, minimums),
            [600, 300, 300],
        )
        # The two trailing panels need their 300px minimum. Only the spare
        # space can go to the first, never artificially reallocate a feasible
        # full-pane 50:25:25 arrangement.
        self.assertEqual(
            ResponsiveSplitter._allocate_preferred_sizes(1000, preferred, minimums),
            [400, 300, 300],
        )
        for width in (861, 900, 950, 1117, 1201, 1440, 1637):
            with self.subTest(width=width):
                sizes = ResponsiveSplitter._allocate_preferred_sizes(
                    width, [0.48, 0.21, 0.31], minimums
                )
                self.assertEqual(sum(sizes), width)
                self.assertTrue(all(n >= m for n, m in zip(sizes, minimums)))

    def test_real_narrow_workspace_uses_soft_minimum_weights_without_collapse(self):
        for preset in ("three_panel_workspace", "validation_three_panel_workspace"):
            with self.subTest(preset=preset):
                page, splitter, frames = self.make_page(preset)
                total = splitter._available_length()
                minimums = splitter_args(preset)["minimums"]
                self.assertLess(total, sum(minimums))
                splitter.apply_responsive_sizes()
                sizes = splitter.sizes()
                self.assertEqual(len(sizes), 3)
                self.assertTrue(all(s >= f.minimumWidth() for s, f in zip(sizes, frames)))
                self.assertAlmostEqual(sum(sizes), total, delta=5)
                self.assertTrue(all(f.isVisible() for f in frames))
                page.close()

    def test_real_minimums_save_restore_and_resize_keep_panels_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            ini = QSettings(str(Path(folder) / "layout.ini"), QSettings.IniFormat)
            with patch("piTrainer.pages.dock_page.QSettings", return_value=ini):
                first, source, _ = self.make_page("three_panel_workspace")
                initial = source.sizes()
                self.assertTrue(all(x > 0 for x in initial))
                first.save_layout()
                ini.sync()
                second, restored, frames = self.make_page("three_panel_workspace")
                second.restore_layout()
                self.app.processEvents()
                self.assertTrue(all(n >= f.minimumWidth() for n, f in zip(restored.sizes(), frames)))
                # A restored narrow workspace cannot retain full soft widths,
                # but should not arbitrarily discard panes or saved layout.
                widths = restored.sizes()
                for x, y in zip(widths, initial):
                    self.assertAlmostEqual(x, y, delta=14)
                second.resize(max(480, second.width() - 55), second.height())
                self.app.processEvents()
                self.assertTrue(all(n >= f.minimumWidth() for n, f in zip(restored.sizes(), frames)))
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()
