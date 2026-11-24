"""R50: real Qt Validation Review -> MainWindow route -> Data source selection.

Fixtures are disposable, use tiny images and never write to user records.
"""
from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QTabWidget

from piTrainer.app_state import AppState
from piTrainer.main_window import MainWindow
from piTrainer.pages.data_page import DataPage
from piTrainer.panels.data.session_source_panel import SessionSourcePanel
from piTrainer.panels.validation.validation_frame_review_panel import (
    ValidationFrameReviewPanel,
)


# Valid 1x1 PNG; no camera, drive, or model runtime involved.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9U9H0AAAAASUVORK5CYII="
)


class WindowHarness:
    def __init__(self):
        self.tabs = QTabWidget()
        self.data_page = None
        self.messages = []
        self.load_events = 0

    def set_status_message(self, message):
        self.messages.append(str(message))

    def on_dataset_loaded(self):
        self.load_events += 1

    def sync_working_folder_from_loaded_sessions(self, show_status=True):
        return None


class ValidationToDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def create_session(root: Path, name: str):
        session = root / name
        frames = session / "frames"
        frames.mkdir(parents=True)
        (frames / "f01.png").write_bytes(PNG)
        record = {
            "frame_id": "f01", "frame": "frames/f01.png", "ts": name + "-time",
            "mode": "manual", "steering": 0.15, "throttle": 0.45,
        }
        (session / "labels.jsonl").write_text(
            json.dumps(record) + "\n", encoding="utf-8"
        )
        return str((frames / "f01.png").resolve())

    def make_workspace(self, root: Path, settings):
        state = AppState(records_root=str(root))
        shell = WindowHarness()
        with patch("piTrainer.pages.dock_page.QSettings", return_value=settings), \
             patch.object(SessionSourcePanel, "_settings", lambda _self: settings):
            data = DataPage(state, shell)
        shell.data_page = data
        review = ValidationFrameReviewPanel(
            edit_in_data_callback=lambda record:
            MainWindow.open_validation_frame_in_data_editor(shell, record)
        )
        shell.tabs.addTab(data, "1 Data")
        shell.tabs.addTab(review, "4 Validate")
        self.addCleanup(shell.tabs.close)
        self.addCleanup(shell.tabs.deleteLater)
        shell.tabs.resize(940, 610)
        shell.tabs.show()
        self.app.processEvents()
        data.session_source_panel.set_sessions(["session-a", "session-b"])
        data.session_source_panel.set_selected_sessions(["session-a"])
        data.load_selected_sessions()
        self.app.processEvents()
        self.assertEqual(set(state.dataset_df["session"]), {"session-a"})
        return shell, review, state

    @staticmethod
    def validation_row(session, frame_id, source_frame_id="", variant=""):
        return {
            "rows_used": 1, "sessions": [session], "frame_ids": [frame_id],
            "timestamps": [session + "-prediction"], "abs_images": [""],
            "source_frame_ids": [source_frame_id],
            "synthetic_variants": [variant],
            "aug_flip_lr": [bool(variant)],
            "steering_true": [0.2], "steering_pred": [0.1],
            "throttle_true": [0.5], "throttle_pred": [0.4],
            "combined_error": [0.2],
        }

    def test_unloaded_synthetic_source_reloads_and_selects_correct_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "records"
            image_a = self.create_session(root, "session-a")
            image_b = self.create_session(root, "session-b")
            settings = QSettings(
                str(Path(folder) / "trainer.ini"), QSettings.IniFormat
            )
            shell, review, state = self.make_workspace(root, settings)
            self.assertEqual(
                shell.data_page.preview_panel.selected_record()["abs_image"], image_a
            )
            review.set_result(self.validation_row(
                "session-b", "s_f01", source_frame_id="f01", variant="flip_lr"
            ))
            shell.tabs.setCurrentIndex(1)
            review._edit_current_frame()
            self.app.processEvents()
            self.assertEqual(shell.tabs.currentIndex(), 0)
            self.assertEqual(
                shell.data_page.preview_panel.selected_record()["abs_image"], image_b
            )
            self.assertEqual(shell.data_page.preview_panel.selected_record()["frame_id"], "f01")
            self.assertTrue(shell.data_page.last_focus_redirected_to_source)
            self.assertEqual(shell.data_page.last_focus_source_frame_id, "f01")
            self.assertEqual(shell.data_page.session_source_panel.selected_sessions(),
                             ["session-a", "session-b"])
            self.assertEqual(state.selected_sessions, ["session-a", "session-b"])
            self.assertEqual(shell.load_events, 2)
            self.assertIn("redirecting to source frame", shell.messages[-1])
            # Revisit Validate and preserve the exact original synthetic row.
            shell.tabs.setCurrentIndex(1)
            review.restore_pending_selection()
            self.assertEqual(review.selected_row()["frame_id"], "s_f01")

    def test_loaded_source_does_not_reload_or_clear_multi_session_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "records"
            self.create_session(root, "session-a")
            self.create_session(root, "session-b")
            settings = QSettings(str(Path(folder) / "trainer.ini"), QSettings.IniFormat)
            shell, review, state = self.make_workspace(root, settings)
            shell.data_page.session_source_panel.set_selected_sessions(
                ["session-a", "session-b"]
            )
            review.set_result(self.validation_row("session-a", "f01"))
            shell.tabs.setCurrentIndex(1)
            review._edit_current_frame()
            self.app.processEvents()
            self.assertEqual(shell.tabs.currentIndex(), 0)
            self.assertEqual(shell.data_page.preview_panel.selected_record()["session"],
                             "session-a")
            self.assertEqual(state.selected_sessions, ["session-a", "session-b"])
            self.assertEqual(shell.load_events, 1)


if __name__ == "__main__":
    unittest.main()
