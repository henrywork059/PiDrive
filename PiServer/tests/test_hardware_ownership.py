"""Tests for exclusive Pi hardware ownership, independent of real GPIO/camera."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from piserver.core.hardware_ownership import HardwareOwnershipError, claim_hardware
from piserver.services import camera_service as camera_module
from piserver.services import motor_service as motor_module


class FakePWM:
    def __init__(self):
        self.cycles = []

    def start(self, duty):
        self.cycles.append(duty)

    def ChangeDutyCycle(self, duty):
        self.cycles.append(duty)


class FakeGPIO:
    BCM = 11
    OUT = 1

    def __init__(self):
        self.pwms = []
        self.cleanup_calls = 0

    def setmode(self, mode):
        pass

    def setwarnings(self, warnings):
        pass

    def setup(self, *args):
        pass

    def PWM(self, *args):
        pwm = FakePWM()
        self.pwms.append(pwm)
        return pwm

    def cleanup(self):
        self.cleanup_calls += 1


@unittest.skipUnless(os.name == 'posix', 'Linux/POSIX file locking required')
class HardwareOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lock_path = Path(self.temp.name) / 'shared.lock'
        self.env_patch = patch.dict(os.environ, {'PIDRIVE_HARDWARE_LOCK_FILE': str(self.lock_path)})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def child_lease_check(self, expected_ok: bool):
        script = (
            'from piserver.core.hardware_ownership import claim_hardware; '
            'lease=claim_hardware("motor"); print("ACQUIRED"); lease.release()'
        )
        env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
        result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True, timeout=5)
        if expected_ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ACQUIRED', result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Physical camera/motor hardware is already in use', result.stderr)

    def test_two_resources_share_same_owner_but_second_motor_is_denied(self):
        camera = claim_hardware('camera')
        self.addCleanup(camera.release)
        motor = claim_hardware('motor')
        self.addCleanup(motor.release)
        with self.assertRaisesRegex(HardwareOwnershipError, 'already opened in this process'):
            claim_hardware('motor')
        self.child_lease_check(expected_ok=False)
        camera.release()
        self.child_lease_check(expected_ok=False)
        motor.release()
        self.child_lease_check(expected_ok=True)

    def test_abrupt_process_exit_releases_lock_without_file_deletion(self):
        script = 'from piserver.core.hardware_ownership import claim_hardware; import time; lease=claim_hardware("camera"); print("READY", flush=True); time.sleep(30)'
        env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
        child = subprocess.Popen([sys.executable, '-u', '-c', script], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'READY')
            with self.assertRaises(HardwareOwnershipError):
                claim_hardware('motor')
        finally:
            child.kill()
            child.communicate(timeout=5)
        owner = claim_hardware('motor')
        owner.release()
        self.assertTrue(self.lock_path.exists(), 'Stable lock file inode must never be removed')

    def test_gpio_driver_is_exclusive_and_released_after_stop(self):
        gpio = FakeGPIO()
        with patch.object(motor_module, 'GPIO_AVAILABLE', True), patch.object(motor_module, 'GPIO', gpio):
            one = motor_module.MotorService()
            self.addCleanup(one.close)
            one.update(0.1, 0.3, 0.5)
            with self.assertRaisesRegex(HardwareOwnershipError, 'already opened'):
                motor_module.MotorService()
            self.child_lease_check(expected_ok=False)
            one.close()
            self.assertEqual(gpio.cleanup_calls, 1)
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                one.update(0, 0.2, 0.5)
            two = motor_module.MotorService()
            self.addCleanup(two.close)
            self.assertEqual((two.last_left, two.last_right), (0.0, 0.0))
            self.assertEqual(gpio.pwms[-1].cycles[0], 0)
            one.close()
            self.assertEqual(gpio.cleanup_calls, 1, 'Old runtime must not clean up the new owner')
            two.close()
            self.child_lease_check(expected_ok=True)

    def test_failed_gpio_initialization_does_not_leak_lock(self):
        class BrokenGPIO(FakeGPIO):
            def setmode(self, mode):
                raise RuntimeError('GPIO initialization failed')
        with patch.object(motor_module, 'GPIO_AVAILABLE', True), patch.object(motor_module, 'GPIO', BrokenGPIO()):
            with self.assertRaisesRegex(RuntimeError, 'GPIO initialization failed'):
                motor_module.MotorService()
        self.child_lease_check(expected_ok=True)

    def test_camera_acquires_before_open_and_shares_motor_process_lock(self):
        gpio = FakeGPIO()
        with (patch.object(camera_module, 'Picamera2', object()),
              patch.object(camera_module.CameraService, '_open_backend_locked'),
              patch.object(camera_module.CameraService, '_loop', lambda self: None),
              patch.object(motor_module, 'GPIO_AVAILABLE', True),
              patch.object(motor_module, 'GPIO', gpio)):
            cam = camera_module.CameraService()
            cam.start()
            self.addCleanup(cam.stop)
            owner = motor_module.MotorService()
            self.addCleanup(owner.close)
            second = camera_module.CameraService()
            with self.assertRaisesRegex(HardwareOwnershipError, 'already opened'):
                second.start()
            cam.stop()
            self.child_lease_check(expected_ok=False)
            owner.close()
            self.child_lease_check(expected_ok=True)

    def test_failed_gpio_cleanup_retains_lock_until_safe_shutdown(self):
        class UnreliableGPIO(FakeGPIO):
            fail_cleanup = True

            def cleanup(self):
                if self.fail_cleanup:
                    raise RuntimeError('could not clean up hardware')
                super().cleanup()

        gpio = UnreliableGPIO()
        with patch.object(motor_module, 'GPIO_AVAILABLE', True), patch.object(motor_module, 'GPIO', gpio):
            service = motor_module.MotorService()
            self.addCleanup(service.close)
            with self.assertRaisesRegex(RuntimeError, 'could not clean up hardware'):
                service.close()
            self.child_lease_check(expected_ok=False)
            gpio.fail_cleanup = False
            service.close()
            self.child_lease_check(expected_ok=True)

    def test_unstopped_camera_thread_prevents_hardware_handover(self):
        class HungThread:
            alive = True

            def is_alive(self):
                return self.alive

            def join(self, timeout):
                return None

        with patch.object(camera_module, 'Picamera2', object()), patch.object(camera_module.CameraService, '_release_backends_locked'):
            camera = camera_module.CameraService()
            camera._hardware_lease = claim_hardware('camera')
            self.addCleanup(camera.close)
            old_thread = HungThread()
            camera._thread = old_thread
            camera._running = True
            with self.assertRaisesRegex(RuntimeError, 'hardware lease retained'):
                camera.close()
            self.child_lease_check(expected_ok=False)
            with self.assertRaisesRegex(RuntimeError, 'capture thread is still active'):
                camera.start()
            old_thread.alive = False
            camera.close()
            self.child_lease_check(expected_ok=True)

    def test_motor_simulation_remains_unrestricted(self):
        with patch.object(motor_module, 'GPIO_AVAILABLE', False):
            first = motor_module.MotorService()
            second = motor_module.MotorService()
            self.addCleanup(first.close)
            self.addCleanup(second.close)
            first.update(0, .1, .5)
            second.update(0, .2, .5)
            self.assertFalse(self.lock_path.exists())


class PerformancePlaceholderTests(unittest.TestCase):
    def test_idle_live_capture_does_not_rebuild_unused_placeholder(self):
        import threading
        from unittest.mock import Mock
        from types import SimpleNamespace
        svc = SimpleNamespace(
            _running=True, _service_lock=threading.RLock(), _frame_lock=threading.RLock(),
            _desired_capture_fps_locked=lambda: 100, preview_fps=12,
            preview_enabled=False, processing_enabled=False,
            _picam2=object(), _capture=None, _frame=None, _raw_frame=None,
            performance=Mock(), _placeholder_frame=Mock(return_value=object()),
            _publish_jpeg=Mock(),
        )
        captures = []
        def capture(need_frame, need_preview):
            captures.append((need_frame, need_preview))
            if len(captures) == 4:
                svc._running = False
            return None, None, True, ""
        svc._capture_picamera_request = capture
        svc.preview_resource_profile = "standard"
        svc._effective_preview_fps = lambda: camera_module.CameraService._effective_preview_fps(svc)
        camera_module.CameraService._loop(svc)
        self.assertEqual(captures, [(False, False)] * 4)
        svc._placeholder_frame.assert_called_once_with()
        svc._publish_jpeg.assert_not_called()
        self.assertIsNotNone(svc._frame)
        self.assertIsNone(svc._raw_frame)


class PerformancePILConversionParityTests(unittest.TestCase):
    def test_owned_bgr_pixels_for_pil_modes_and_numpy_fallback(self):
        from unittest.mock import patch
        import numpy as np
        from PIL import Image
        from piserver.services import camera_service as cm
        rng=np.random.default_rng(17)
        image=Image.fromarray(rng.integers(0,256,(240,426,3),dtype=np.uint8))
        for backend in (cm.cv2,None):
            with patch.object(cm,"cv2",backend):
                for mode in ("RGB","RGBA","L","P","CMYK","I","F","1"):
                    source=image.convert(mode)
                    arr=np.array(source)
                    if arr.ndim==2:
                        expected=backend.cvtColor(arr,backend.COLOR_GRAY2BGR) if backend is not None and arr.dtype in (np.uint8,np.uint16,np.float32) else np.stack([arr]*3,axis=-1)
                    else:
                        expected=arr[:,:,:3][:,:,::-1].copy() if arr.ndim==3 and arr.shape[2]>=3 else arr.copy()
                    actual=cm.CameraService()._frame_from_pil(source)
                    if backend is not None and arr.ndim==2 and arr.dtype not in (np.uint8,np.uint16,np.float32):
                        # Legacy OpenCV rejects these grayscale dtypes.
                        self.assertIsNone(actual)
                        continue
                    np.testing.assert_array_equal(actual,expected)
                    self.assertEqual(actual.dtype,expected.dtype)
                    self.assertTrue(actual.flags.writeable)
                    actual.flat[0]=0
                    np.testing.assert_array_equal(np.array(source),arr)


if __name__ == '__main__':
    unittest.main()
