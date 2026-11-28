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

    def test_m02_stop_event_blocks_late_prediction_commit(self):
        service = self.make_service()
        motor = CapturingMotor()
        service._ensure_model_ready_for_run = lambda: None
        def prediction(_):
            # STOP arrived during inference, before the actuator commit.
            service._stop_event.set()
            return (0.4, 0.3)
        service._predict_from_jpeg = prediction
        service._running = True
        service._mode = "drive"
        service._drive_output_enabled = True
        result = service.predict_once(StaticCamera(), motor, drive=True)
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(motor.commands, [])

    def test_m02_commit_is_serialized_with_override(self):
        import threading
        service = self.make_service()
        service._ensure_model_ready_for_run = lambda: None
        service._predict_from_jpeg = lambda _: (0.4, 0.3)
        service._running = True
        service._mode = "drive"
        service._drive_output_enabled = True
        entered = threading.Event()
        release = threading.Event()
        override_started = threading.Event()
        override_done = threading.Event()
        motor = CapturingMotor()
        original = motor.update
        def update(**kwargs):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("test barrier timeout")
            return original(**kwargs)
        motor.update = update
        results = []
        prediction = threading.Thread(target=lambda: results.append(service.predict_once(StaticCamera(), motor, drive=True)))
        def override():
            override_started.set()
            service.keep_preview_for_manual_override(motor, stop_motors=True)
            override_done.set()
        other = threading.Thread(target=override)
        prediction.start()
        try:
            self.assertTrue(entered.wait(2))
            other.start()
            self.assertTrue(override_started.wait(2))
            self.assertFalse(override_done.wait(0.1), "override escaped the commit lock")
        finally:
            release.set()
            prediction.join(4)
            if other.ident is not None:
                other.join(4)
        self.assertFalse(prediction.is_alive())
        self.assertFalse(other.is_alive())
        self.assertTrue(override_done.is_set())
        self.assertTrue(results[0].get("ok"), results)
        self.assertEqual(len(motor.commands), 1)
        self.assertFalse(service.status()["drive_output_enabled"])
        service.predict_once(StaticCamera(), motor, drive=True)
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


class PerformanceSimulationParityTests(unittest.TestCase):
    def test_static_geometry_and_lut_preserve_pixels_across_sizes_and_sequences(self):
        from unittest.mock import patch
        import numpy as np
        from pisd.services import camera_service as cm
        camera = cm.CameraService(hardware_enabled=False)
        cv = cm.cv2
        for backend in (cv, None):
            with patch.object(cm, "cv2", backend):
                for width, height in ((426,240),(160,120),(640,480),(426,240)):
                    camera.config.width, camera.config.height = width, height
                    previous = None
                    for seq in (0,1,36,37,51,52,85,86,255,256,1000,10000):
                        camera.frame_seq = seq
                        x = np.linspace(0,255,width,dtype=np.uint8)
                        y = np.linspace(0,255,height,dtype=np.uint8)[:,None]
                        expected = np.zeros((height,width,3),dtype=np.uint8)
                        try:
                            expected[:,:,0] = (x[None,:]+seq*3)%255
                            expected[:,:,1] = (y+seq*5)%255
                            expected[:,:,2] = ((x[None,:]//2+y//2+seq*7)%255).astype(np.uint8)
                        except OverflowError:
                            # NumPy 2 changed scalar promotion. Match legacy
                            # exception semantics rather than silently alter pixels.
                            with self.assertRaises(OverflowError):
                                camera._make_simulated_frame()
                            continue
                        if backend is not None:
                            backend.putText(expected,f"PiSD SIM {seq}",(12,max(24,height//8)),
                                            backend.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2,backend.LINE_AA)
                        actual = camera._make_simulated_frame()
                        np.testing.assert_array_equal(actual,expected)
                        self.assertTrue(actual.flags.c_contiguous)
                        self.assertTrue(actual.flags.writeable)
                        if previous is not None:
                            self.assertFalse(np.shares_memory(previous,actual))
                        previous=actual
                        if backend is not None:
                            params = [int(backend.IMWRITE_JPEG_QUALITY), 60]
                            ok, encoded = backend.imencode(".jpg", actual, params)
                            ref_ok, ref_encoded = backend.imencode(".jpg", expected, params)
                            self.assertTrue(ok and ref_ok)
                            self.assertEqual(encoded.tobytes(), ref_encoded.tobytes())
        if cv is not None:
            camera.config.width, camera.config.height = 426, 240
            camera.frame_seq = 25
            expected = camera._make_simulated_frame()
            with patch.object(cv, "merge", side_effect=RuntimeError("test fallback")):
                np.testing.assert_array_equal(camera._make_simulated_frame(), expected)

    def test_request_pil_conversion_preserves_pixels_jpeg_and_request_release(self):
        from unittest.mock import patch, Mock
        import numpy as np
        from PIL import Image
        from pisd.services import camera_service as cm
        camera = cm.CameraService({"width":426,"height":240,"preview_quality":60},hardware_enabled=False)
        rng = np.random.default_rng(17)
        image = Image.fromarray(rng.integers(0,256,(240,426,3),dtype=np.uint8))
        for backend in (cm.cv2, None):
            with patch.object(cm,"cv2",backend):
                for mode in ("RGB","RGBA","L","P","CMYK","I","F","1"):
                    source = image.convert(mode)
                    arr = np.array(source)
                    if arr.ndim == 2 and backend is not None and arr.dtype not in (np.uint8,np.uint16,np.float32):
                        self.assertIsNone(camera._frame_from_pil(source))
                        continue
                    if arr.ndim == 2:
                        expected = backend.cvtColor(arr,backend.COLOR_GRAY2BGR) if backend is not None else np.stack([arr]*3,axis=-1)
                    else:
                        expected = arr[:,:,:3][:,:,::-1].copy() if arr.ndim==3 and arr.shape[2]>=3 else arr.copy()
                    actual = camera._frame_from_pil(source)
                    np.testing.assert_array_equal(actual,expected)
                    self.assertEqual(actual.dtype,expected.dtype)
                    self.assertTrue(actual.flags.writeable)
                    actual.flat[0] = 0
                    np.testing.assert_array_equal(np.array(source),arr)
        if cm.cv2 is not None:
            expected = np.array(image)[:,:,::-1].copy()
            with patch.object(cm.cv2,"cvtColor",side_effect=RuntimeError("test fallback")):
                np.testing.assert_array_equal(camera._frame_from_pil(image),expected)
        import io
        buf = io.BytesIO()
        image.save(buf,format="JPEG",quality=60,optimize=False)
        request = Mock()
        request.make_image.return_value = image
        request.get_metadata.return_value = {"ExposureTime":1000,"SensorTimestamp":123}
        camera._picam2 = Mock()
        camera._picam2.capture_request.return_value = request
        frame,jpeg = camera._capture_picamera_request()
        np.testing.assert_array_equal(frame,np.array(image)[:,:,::-1])
        self.assertEqual(jpeg,buf.getvalue())
        request.release.assert_called_once()
        self.assertEqual(camera._last_capture_source,"request")
        self.assertEqual(camera._last_metadata["SensorTimestamp"],123)
        request.reset_mock()
        request.make_image.side_effect = RuntimeError("capture failure")
        with self.assertRaisesRegex(RuntimeError,"capture failure"):
            camera._capture_picamera_request()
        request.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
