"""R38 deterministic cache/selection tests without a PySide6 installation.

The cache uses stub Qt objects solely to exercise eviction and signatures.
Render-method tests extract the exact production methods with ast and execute
them against a controlled fake Qt event loop. Run real Qt flip tests separately
on the Windows desktop before promoting the PR.
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE_ROOT = Path(__file__).resolve().parents[1] / 'piTrainer'


class FakeTransform:
    def __init__(self):
        self.x = 1

    def scale(self, x, _y):
        self.x = x
        return self


class FakePixmap:
    opens = 0

    def __init__(self, path):
        type(self).opens += 1
        try:
            width, height = map(int, Path(path).read_text().strip().split(','))
        except (OSError, ValueError):
            width, height = 0, 0
        self.w, self.h, self.flipped = width, height, False

    @classmethod
    def new(cls, width, height, flipped=False):
        result = object.__new__(cls)
        result.w, result.h, result.flipped = width, height, flipped
        return result

    def width(self):
        return self.w

    def height(self):
        return self.h

    def depth(self):
        return 32

    def isNull(self):
        return self.w <= 0 or self.h <= 0

    def transformed(self, transform, _quality):
        return self.new(self.w, self.h, self.flipped ^ (transform.x < 0))

    def scaled(self, width, height, _aspect, _quality):
        factor = min(width / self.w, height / self.h)
        return self.new(int(self.w * factor), int(self.h * factor), self.flipped)


def load_cache_module():
    package = types.ModuleType('PySide6')
    package.__path__ = []
    core = types.ModuleType('PySide6.QtCore')
    core.Qt = types.SimpleNamespace(SmoothTransformation=1, KeepAspectRatio=2)
    gui = types.ModuleType('PySide6.QtGui')
    gui.QPixmap = FakePixmap
    gui.QTransform = FakeTransform
    overrides = {'PySide6': package, 'PySide6.QtCore': core, 'PySide6.QtGui': gui}
    spec = importlib.util.spec_from_file_location('r38_isolated_image_utils', SOURCE_ROOT / 'utils/image_utils.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, overrides):
        spec.loader.exec_module(module)
    return module


class CacheBudgetTests(unittest.TestCase):
    def setUp(self):
        self.cache = load_cache_module()
        FakePixmap.opens = 0
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)

    def frame(self, name, width=1920, height=1080):
        path = Path(self.root.name) / (str(name) + '.img')
        path.write_text(f'{width},{height}')
        return str(path)

    def test_decoded_pixel_bytes_are_bounded_under_repeated_navigation(self):
        for index in range(65):
            self.cache.load_scaled_pixmap(self.frame(index), 1920, 1080)
        stats = self.cache.scaled_pixmap_cache_stats()
        self.assertLessEqual(stats['estimated_bytes'], 64 * 1024 * 1024)
        self.assertLessEqual(stats['items'], 96)

    def test_lru_hit_does_not_redecode(self):
        path = self.frame('one')
        first = self.cache.load_scaled_pixmap(path, 640, 480)
        second = self.cache.load_scaled_pixmap(path, 640, 480)
        self.assertIs(first, second)
        self.assertEqual(FakePixmap.opens, 1)

    def test_flip_is_a_distinct_cache_key_and_orientation(self):
        path = self.frame('one')
        normal = self.cache.load_scaled_pixmap(path, 640, 480)
        flipped = self.cache.load_scaled_pixmap(path, 640, 480, True)
        self.assertFalse(normal.flipped)
        self.assertTrue(flipped.flipped)
        self.assertEqual(self.cache.scaled_pixmap_cache_stats()['items'], 2)

    def test_file_replacement_invalidates_old_scaled_pixels(self):
        path = self.frame('one')
        old = self.cache.load_scaled_pixmap(path, 640, 480)
        Path(path).write_text('640,480')
        st = Path(path).stat()
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 2_000_000_000))
        new = self.cache.load_scaled_pixmap(path, 640, 480)
        self.assertIsNot(old, new)
        self.assertEqual(self.cache.scaled_pixmap_cache_stats()['items'], 1)

    def test_removed_source_is_not_returned_from_cache(self):
        path = self.frame('one')
        self.cache.load_scaled_pixmap(path, 640, 480)
        Path(path).unlink()
        self.assertIsNone(self.cache.load_scaled_pixmap(path, 640, 480))

    def test_oversized_pixmap_is_delivered_but_not_cached(self):
        path = self.frame('big', 10000, 10000)
        self.assertIsNotNone(self.cache.load_scaled_pixmap(path, 10000, 10000))
        self.assertEqual(self.cache.scaled_pixmap_cache_stats()['items'], 0)

    def test_existing_96_item_cap_is_still_respected(self):
        for index in range(110):
            self.cache.load_scaled_pixmap(self.frame(index, 64, 64), 64, 64)
        self.assertEqual(self.cache.scaled_pixmap_cache_stats()['items'], 96)

    def test_cache_clear_releases_accounted_pixel_memory(self):
        self.cache.load_scaled_pixmap(self.frame('a'), 640, 480)
        self.cache.clear_scaled_pixmap_cache()
        stats = self.cache.scaled_pixmap_cache_stats()
        self.assertEqual(stats['estimated_bytes'], 0)
        self.assertEqual(stats['items'], 0)


class FakeTimer:
    def __init__(self):
        self.live = False
        self.callback = None

    def stop(self):
        self.live = False

    def start(self):
        self.live = True

    def fire(self):
        if self.live:
            self.live = False
            self.callback()


class FakeLabel:
    def __init__(self):
        self.image = None
        self.message = ''

    def set_display_pixmap(self, image):
        self.image = image

    def setText(self, text):
        self.message = text


class PreviewGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((SOURCE_ROOT / 'panels/data/image_preview_panel.py').read_text(encoding='utf-8'))
        panel = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'ImagePreviewPanel')
        cls.methods = {}
        for method in panel.body:
            if not isinstance(method, ast.FunctionDef) or method.name not in {'set_record', 'clear_preview', '_render_preview'}:
                continue
            scope = {'Any': object, 'truthy_value': lambda value, default=False: bool(value),
                     'DATA_OVERLAY_TEXT_COLOR': None, 'DATA_OVERLAY_TEXT_SCALE': 1.0}
            parsed = ast.Module(body=[
                ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                copy.deepcopy(method),
            ], type_ignores=[])
            exec(compile(ast.fix_missing_locations(parsed), '<production-preview-method>', 'exec'), scope)
            cls.methods[method.name] = scope[method.name]

    def make_panel(self):
        panel = types.SimpleNamespace()
        panel._render_generation = 0
        panel.current_record = None
        panel.selection_render_timer = FakeTimer()
        panel.resize_render_timer = FakeTimer()
        panel.image_label = FakeLabel()
        panel.overlay_options = {'speed_vertical': True}
        panel.current_label = None
        panel._sync_controls_from_record = lambda: setattr(panel, 'current_label', panel.current_record['frame_id'])
        panel._record_edit_key = lambda record: (record.get('frame_id'), record.get('abs_image'))
        panel._preview_size = lambda: (640, 360)
        panel._set_slider_enabled = lambda value: None
        panel.steering_slider = types.SimpleNamespace(setValue=lambda value: None)
        panel.speed_slider = types.SimpleNamespace(setValue=lambda value: None)
        panel._update_value_labels = lambda *args: None
        panel._update_overlay_meta_label = lambda *args: None
        panel._has_deployed_output = lambda record: False
        for name, method in self.methods.items():
            setattr(panel, name, types.MethodType(method, panel))
        panel.selection_render_timer.callback = panel._render_preview
        panel.resize_render_timer.callback = panel._render_preview
        return panel

    @staticmethod
    def record(frame_id, flip=False):
        return {'frame_id': frame_id, 'abs_image': frame_id + '.jpg',
                'steering': .2, 'throttle': .4, 'aug_flip_lr': flip}

    def stub_render(self, *, loader, painter):
        self.methods['_render_preview'].__globals__.update({
            'load_scaled_pixmap': loader,
            'apply_overlays': painter,
            'apply_prediction_comparison_overlay': lambda *args, **kwargs: None,
        })

    def test_rapid_selection_coalesces_to_latest_frame(self):
        panel, calls = self.make_panel(), []
        self.stub_render(loader=lambda path, **kw: calls.append(path) or path,
                         painter=lambda image, record, options: ('paint', image, record['frame_id']))
        for frame_id in ('a', 'b', 'c'):
            panel.set_record(self.record(frame_id))
        self.assertEqual(calls, [])
        self.assertIsNone(panel.image_label.image)
        self.assertEqual(panel.current_label, 'c')
        panel.selection_render_timer.fire()
        self.assertEqual(calls, ['c.jpg'])
        self.assertEqual(panel.image_label.image, ('paint', 'c.jpg', 'c'))

    def test_previous_image_cleared_before_new_labels_are_visible(self):
        panel = self.make_panel()
        self.stub_render(loader=lambda path, **kw: path,
                         painter=lambda image, record, options: image)
        panel.set_record(self.record('a'))
        panel.selection_render_timer.fire()
        self.assertEqual(panel.image_label.image, 'a.jpg')
        panel.set_record(self.record('b'))
        self.assertIsNone(panel.image_label.image)
        self.assertEqual(panel.current_label, 'b')

    def test_clearing_selection_cancels_pending_decode(self):
        panel, calls = self.make_panel(), []
        self.stub_render(loader=lambda path, **kw: calls.append(path) or path,
                         painter=lambda image, record, options: image)
        panel.set_record(self.record('a'))
        panel.clear_preview()
        panel.selection_render_timer.fire()
        self.assertEqual(calls, [])
        self.assertIsNone(panel.image_label.image)

    def test_outdated_result_is_discarded_if_selection_changes_during_decode(self):
        panel, calls = self.make_panel(), []

        def loader(path, **kw):
            calls.append(path)
            if path == 'a.jpg':
                panel.set_record(self.record('b'))
            return path

        self.stub_render(loader=loader, painter=lambda image, record, options: image)
        panel.set_record(self.record('a'))
        panel.selection_render_timer.fire()
        self.assertIsNone(panel.image_label.image)
        panel.selection_render_timer.fire()
        self.assertEqual(panel.image_label.image, 'b.jpg')
        self.assertEqual(calls, ['a.jpg', 'b.jpg'])

    def test_horizontal_flip_reaches_original_loader_and_overlay(self):
        panel, calls = self.make_panel(), []
        self.stub_render(loader=lambda path, **kw: calls.append(kw['flip_lr']) or path,
                         painter=lambda image, record, options: ('paint', image, record['frame_id']))
        panel.set_record(self.record('flipped', True))
        panel.selection_render_timer.fire()
        self.assertEqual(calls, [True])
        self.assertEqual(panel.image_label.image, ('paint', 'flipped.jpg', 'flipped'))


# Optional genuine Qt pixel/overlay tests, in addition to the 13 pure-Python
# policy tests above. Do not treat skipped tests as hardware/GUI validation.
try:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication
    from piTrainer.utils.image_utils import load_scaled_pixmap as qt_load_scaled_pixmap
    from piTrainer.services.data.overlay_service import apply_overlays
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication is not None, 'real PySide6 Qt runtime unavailable')
class RealQtImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_left_right_flip_reverses_pixels_not_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = QImage(8, 4, QImage.Format_RGB32)
            for y in range(4):
                for x in range(8):
                    image.setPixelColor(x, y, QColor('red' if x < 4 else 'blue'))
            path = str(Path(tmp) / 'orientation.png')
            self.assertTrue(image.save(path))
            normal = qt_load_scaled_pixmap(path, 80, 40)
            flipped = qt_load_scaled_pixmap(path, 80, 40, flip_lr=True)
            self.assertGreater(normal.toImage().pixelColor(4, 20).red(), 200)
            self.assertGreater(flipped.toImage().pixelColor(4, 20).blue(), 200)

    def test_existing_overlay_keeps_scaled_image_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = QImage(426, 240, QImage.Format_RGB32)
            image.fill(QColor('#304050'))
            path = str(Path(tmp) / 'overlay.png')
            self.assertTrue(image.save(path))
            base = qt_load_scaled_pixmap(path, 640, 360)
            options = {
                'path_preview': True, 'legacy_path_preview': False,
                'speed_vertical': True, 'steering_horizontal': False,
                'steering_arc': True, 'drive_arrow': False,
            }
            overlaid = apply_overlays(
                base, {'steering': 0.3, 'throttle': 0.4, 'overlay_settings': {}}, options)
            self.assertFalse(overlaid.isNull())
            self.assertEqual(overlaid.size(), base.size())


if __name__ == '__main__':
    unittest.main()
