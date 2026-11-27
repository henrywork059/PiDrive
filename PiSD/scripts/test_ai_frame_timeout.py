#!/usr/bin/env python3
"""Hardware-free checks for PiSD's AI camera freshness safety gate."""

from __future__ import annotations

import tempfile
import time
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.services.ai_drive_service import AIDriveService


class StaticCamera:
    def __init__(self):
        self.frame_seq = 7

    def start(self):
        return True, "ready"

    def get_jpeg_frame_info(self):
        return b"fake-jpeg", self.frame_seq, "", 9


class CapturingMotor:
    hardware_enabled = False

    def __init__(self):
        self.commands = []
        self.stop_count = 0

    def update(self, *, steering, throttle, control_source="other"):
        self.commands.append((steering, throttle))
        return throttle - steering, throttle + steering

    def status(self):
        return {"last_intended_left": 0.2, "last_intended_right": 0.4}

    def stop(self):
        self.stop_count += 1


class AICameraFreshnessTests(unittest.TestCase):
    def make_service(self, **settings):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        service = AIDriveService(
            Path(workspace.name),
            {"command_timeout_s": 0.75, "steering_smoothing": 0.0,
             "throttle_smoothing": 0.0, **settings},
        )
        self.addCleanup(service.close)
        return service

    def test_same_frame_expires_and_new_sequence_renews(self):
        service = self.make_service()
        service._assert_fresh_frame_seq(9, now_monotonic=10.0)
        service._assert_fresh_frame_seq(9, now_monotonic=10.7)
        with self.assertRaisesRegex(RuntimeError, "stale"):
            service._assert_fresh_frame_seq(9, now_monotonic=10.76)
        with self.assertRaisesRegex(RuntimeError, "safety latch"):
            service._assert_fresh_frame_seq(10, now_monotonic=10.77)

    def test_unknown_sequence_is_not_permanently_trusted(self):
        service = self.make_service()
        service._assert_fresh_frame_seq(0, now_monotonic=20.0)
        service._assert_fresh_frame_seq(0, now_monotonic=20.5)
        with self.assertRaisesRegex(RuntimeError, "stale"):
            service._assert_fresh_frame_seq(0, now_monotonic=20.8)

    def test_stale_prediction_stops_motor_and_clears_command(self):
        service = self.make_service()
        camera = StaticCamera()
        motor = CapturingMotor()
        service._ensure_model_ready_for_run = lambda: None
        service._predict_from_jpeg = lambda _: (0.4, 0.3)
        service._running = True
        service._mode = "drive"
        service._drive_output_enabled = True

        first = service.predict_once(camera, motor, drive=True)
        self.assertTrue(first.get("ok"), first)
        self.assertEqual(len(motor.commands), 1)
        with service._lock:
            service._last_fresh_frame_monotonic = time.monotonic() - 1.0

        stale = service.predict_once(camera, motor, drive=True)
        self.assertFalse(stale.get("ok"), stale)
        self.assertEqual(len(motor.commands), 1)
        self.assertGreaterEqual(motor.stop_count, 1)
        status = service.status()
        self.assertTrue(status["camera_frame_stale"])
        self.assertEqual(status["last_safe_command"]["throttle"], 0.0)
        self.assertEqual(status["last_raw_prediction"]["steering"], 0.0)
        self.assertTrue(status["camera_frame_fault_latched"])
        camera.frame_seq = 8
        still_stopped = service.predict_once(camera, motor, drive=True)
        self.assertFalse(still_stopped.get("ok"))
        self.assertEqual(len(motor.commands), 1)

    def test_explicit_restart_state_reset_allows_new_grace_window(self):
        service = self.make_service()
        service._assert_fresh_frame_seq(3, now_monotonic=10.0)
        with service._lock:
            service._last_fresh_frame_seq = 0
            service._last_fresh_frame_monotonic = None
        service._camera_frame_fault_latched = False
        service._assert_fresh_frame_seq(3, now_monotonic=time.monotonic())
        self.assertFalse(service.status()["camera_frame_stale"])


class PerformanceInputParityTests(unittest.TestCase):
    def test_prepare_input_preserves_exact_float_pixels(self):
        import io
        import threading
        from types import SimpleNamespace
        from unittest.mock import Mock
        import numpy as np
        from PIL import Image
        rng = np.random.default_rng(17)
        image = Image.fromarray(rng.integers(0, 256, (240, 426, 3), dtype=np.uint8))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        data = buf.getvalue()
        for size in ((160, 120), (426, 240)):
            svc = SimpleNamespace(performance=Mock(), _input_size=size,
                                  _lock=threading.RLock(), _backend="tflite")
            actual, backend = AIDriveService._prepare_input(svc, data)
            expected = np.asarray(Image.open(io.BytesIO(data)).convert("RGB").resize(size)).astype("float32") / 255.0
            np.testing.assert_array_equal(actual, expected[None, ...])
            self.assertEqual(backend, "tflite")
            self.assertEqual(actual.dtype, np.float32)
            self.assertTrue(actual.flags.c_contiguous)


class PerformanceStreamTests(unittest.TestCase):
    def test_cached_stopped_jpeg_backs_off_and_recovery_publishes(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock
        # Execute the actual nested generator without opening a Pi or server.
        tree = ast.parse((PROJECT_ROOT / "pisd/app.py").read_text(encoding="utf-8"))
        endpoint = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "video_feed")
        generate = next(n for n in endpoint.body if isinstance(n, ast.FunctionDef) and n.name == "generate")
        camera = SimpleNamespace(start=Mock(), wait_for_jpeg_frame=Mock(side_effect=[
            (b"first", 1, "", 5), (b"first", 1, "", 5),
            (b"first", 1, "", 5), (b"second", 2, "", 6)]))
        clock = SimpleNamespace(monotonic=Mock(side_effect=[1.0, 2.0]), sleep=Mock())
        scope = {"camera_service": camera, "time": clock, "_live_preview_interval": lambda: 0.05}
        exec(compile(ast.Module(body=[generate], type_ignores=[]), "video_feed", "exec"), scope)
        stream = scope["generate"]()
        self.assertIn(b"first", next(stream))
        self.assertIn(b"second", next(stream))
        self.assertEqual(clock.sleep.call_count, 2)
        clock.sleep.assert_called_with(0.05)
        self.assertEqual(camera.wait_for_jpeg_frame.call_count, 4)

    def test_same_dtype_input_reuses_owned_tensor_and_integer_parity(self):
        import numpy as np
        x = np.linspace(0, 1, 300, dtype=np.float32).reshape(1, 10, 10, 3)
        before = x.copy()
        self.assertIs(AIDriveService._coerce_tflite_input(x, {"dtype": np.float32}), x)
        for dtype, zero in ((np.int8, -128), (np.uint8, 0)):
            scale = 1 / 255
            limits = np.iinfo(dtype)
            expected = np.clip(np.round(x / scale + zero), limits.min, limits.max).astype(dtype)
            actual = AIDriveService._coerce_tflite_input(x, {"dtype": dtype, "quantization": (scale, zero)})
            np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(x, before)


if __name__ == "__main__":
    unittest.main()
