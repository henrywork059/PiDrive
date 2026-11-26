"""Shared desktop accessibility contracts; no dataset or model writes."""
import unittest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget

from piTrainer.panels.common.log_panel import LogPanel
from piTrainer.panels.common.task_progress_panel import TaskProgressPanel
from piTrainer.ui.layout_widgets import CollapsibleSection
from piTrainer.ui.styles import build_stylesheet
from piTrainer.ui.theme import theme_color


def contrast(a, b):
    def luminance(color):
        values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    values = sorted((luminance(a), luminance(b)))
    return (values[1] + 0.05) / (values[0] + 0.05)


class SharedAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_green_roles_use_contrasting_text_in_all_densities(self):
        dark = theme_color('text_on_warning')
        light = theme_color('text_on_dark')
        for bg, fg in (('success', dark), ('success_hover', dark), ('success_active', light)):
            self.assertGreaterEqual(contrast(theme_color(bg), fg), 4.5)
        for density in ('compact', 'comfortable', 'spacious'):
            css = build_stylesheet(density)
            for selector in ("QPushButton[role='primary']", "QPushButton[role='nextStep']",
                             'QPushButton#pageBannerNextButton', "QLabel[role='saveStatus'][status='saved']",
                             "QLabel[role='preprocessStatus'][status='done']"):
                rule = css.split(selector + ' {', 1)[1].split('}', 1)[0]
                self.assertIn('color: ' + dark, rule)
            self.assertIn('QLabel#backgroundTaskResult:focus', css)
            self.assertIn("QPushButton[role='nextStep'][pulse='true']:pressed", css)

    def test_disclosure_restores_focus_only_when_child_is_hidden(self):
        window = QWidget()
        self.addCleanup(window.close)
        content = QLineEdit('fixture')
        section = CollapsibleSection('Fixture', content)
        other = QPushButton('Other')
        layout = QVBoxLayout(window)
        layout.addWidget(section)
        layout.addWidget(other)
        window.show()
        window.activateWindow()
        self.app.processEvents()
        content.setFocus()
        self.assertTrue(content.hasFocus())
        section.set_expanded(False)
        self.assertTrue(section.toggle_button.hasFocus())
        self.assertFalse(content.isVisible())
        QTest.keyClick(section.toggle_button, Qt.Key_Space)
        self.assertTrue(content.isVisible())
        other.setFocus()
        section.set_expanded(False)
        self.assertTrue(other.hasFocus())

    def test_log_tab_and_progress_result_keyboard_access(self):
        window = QWidget()
        self.addCleanup(window.close)
        log, task = LogPanel('Training'), TaskProgressPanel()
        next_button = QPushButton('Next')
        layout = QVBoxLayout(window)
        for widget in (log, next_button, task):
            layout.addWidget(widget)
        QWidget.setTabOrder(log.text, next_button)
        window.show()
        window.activateWindow()
        self.app.processEvents()
        log.append_line('Synthetic log message')
        self.assertTrue(log.text.isReadOnly())
        self.assertEqual(log.text.accessibleName(), 'Training messages')
        log.text.setFocus()
        QTest.keyClick(log.text, Qt.Key_Tab)
        self.assertTrue(next_button.hasFocus())
        task.begin('Fixture')
        self.assertEqual(task.progress.accessibleName(), 'Task progress')
        self.assertEqual(task.progress.accessibleDescription(), 'Running: Fixture')
        self.assertEqual(task.progress.maximum(), 0)
        task.set_step('Checking', 42)
        self.assertEqual(task.progress.value(), 42)
        self.assertEqual(task.progress.accessibleDescription(), 'Checking')
        task.succeed('Done', ['fixture.tflite'])
        self.assertEqual(task.progress.value(), 100)
        self.assertEqual(task.progress.accessibleDescription(), 'Succeeded: Done')
        task.result_label.setFocus()
        QTest.keyClick(task.result_label, Qt.Key_A, Qt.ControlModifier)
        self.assertIn('fixture.tflite', task.result_label.selectedText())
        task.fail('Synthetic error')
        self.assertEqual(task.progress.accessibleDescription(), 'Failed')
        task.cancel('Synthetic cancellation')
        self.assertEqual(task.progress.accessibleDescription(), 'Cancelled')
        task.stop_requested()
        self.assertIn('Stop requested', task.progress.accessibleDescription())


if __name__ == '__main__':
    unittest.main()
