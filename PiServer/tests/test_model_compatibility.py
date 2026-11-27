"""Model TFLite tensor-contract regression tests; no real Pi hardware or TF required."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import numpy as np
    import cv2
except ImportError:  # pragma: no cover
    np = None
    cv2 = None

from piserver.services import model_service as module
from piserver.services.model_service import ModelService


class FakeInterpreter:
    specs = {}
    instances = []

    def __init__(self, model_path):
        name = Path(model_path).name
        self.config = dict(self.specs[name])
        self.input = None
        self.inference_count = 0
        self.instances.append(self)

    def allocate_tensors(self):
        if self.config.get('bad_allocation'):
            raise RuntimeError('allocate failed')

    def get_input_details(self):
        shape = self.config.get('shape', (1, 120, 160, 3))
        result = {
            'shape': np.array(shape, dtype=np.int32),
            'index': 0,
            'dtype': self.config.get('input_dtype', np.float32),
            'quantization': self.config.get('input_quant', (0.0, 0)),
        }
        return [result] * self.config.get('inputs', 1)

    def get_output_details(self):
        shape = self.config.get('output_shape', (1, 2))
        result = {
            'shape': np.array(shape, dtype=np.int32),
            'index': 1,
            'dtype': self.config.get('output_dtype', np.float32),
            'quantization': self.config.get('output_quant', (0.0, 0)),
        }
        return [result] * self.config.get('outputs', 1)

    def set_tensor(self, index, x):
        assert index == 0
        assert tuple(x.shape) == tuple(self.get_input_details()[0]['shape']), f'input tensor shape {x.shape}'
        assert x.dtype == np.dtype(self.get_input_details()[0]['dtype']), f'input dtype {x.dtype}'
        self.input = x.copy()

    def invoke(self):
        self.inference_count += 1
        if self.config.get('bad_invoke'):
            raise RuntimeError('inference failed')

    def get_tensor(self, index):
        assert index == 1
        data = self.config.get('output', (0.25, 0.5))
        return np.asarray(data, dtype=self.get_output_details()[0]['dtype']).reshape(self.config.get('output_shape', (1, 2)))


@unittest.skipUnless(np is not None and cv2 is not None, 'NumPy and OpenCV required')
class ModelCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = ModelService(self.tmp.name)
        FakeInterpreter.specs = {}
        FakeInterpreter.instances = []
        patcher = patch.object(module, 'InterpreterType', FakeInterpreter)
        patcher.start()
        self.addCleanup(patcher.stop)

    def add_model(self, name, **config):
        Path(self.tmp.name, name).write_bytes(b'TFL3-dummy')
        FakeInterpreter.specs[name] = config

    def test_exported_160x120_float_model_resizes_dynamically(self):
        self.add_model('export.tflite', shape=(1, 120, 160, 3))
        ok, message = self.svc.load_model('export.tflite')
        self.assertTrue(ok, message)
        self.assertEqual(self.svc.get_input_spec(), {'width': 160, 'height': 120, 'channels': 3, 'dtype': 'float32'})
        # One pixel BGR is converted to RGB and normalized like piTrainer's dataset loader.
        frame = np.array([[[10, 20, 30]]], dtype=np.uint8)
        self.assertEqual(self.svc.predict_uv_from_frame(frame), (0.25, 0.5))
        inp = FakeInterpreter.instances[-1].input
        self.assertEqual(inp.shape, (1, 120, 160, 3))
        np.testing.assert_allclose(inp[0, 0, 0], [30/255, 20/255, 10/255], atol=1e-6)

    def test_legacy_200x112_input_continues_to_work(self):
        self.add_model('legacy.tflite', shape=(1, 112, 200, 3))
        self.assertTrue(self.svc.load_model('legacy.tflite')[0])
        self.assertEqual(self.svc.get_input_spec()['width'], 200)
        self.assertEqual(self.svc.get_input_spec()['height'], 112)
        self.assertIsNotNone(self.svc.predict_uv_from_frame(np.zeros((4, 4, 3), np.uint8)))
        self.assertEqual(FakeInterpreter.instances[-1].input.shape, (1, 112, 200, 3))

    def test_quantized_model_round_trip(self):
        self.add_model('quant.tflite', shape=(1, 120, 160, 3), input_dtype=np.uint8,
                       input_quant=(1/255, 0), output_dtype=np.int8,
                       output_quant=(0.01, -100), output=(-75, -55))
        self.assertTrue(self.svc.load_model('quant.tflite')[0])
        self.assertEqual(self.svc.get_input_spec()['dtype'], 'uint8')
        cmd = self.svc.predict_uv_from_frame(np.full((20, 20, 3), 255, np.uint8))
        self.assertAlmostEqual(cmd[0], 0.25, places=5)
        self.assertAlmostEqual(cmd[1], 0.45, places=5)
        inp = FakeInterpreter.instances[-1].input
        self.assertEqual(inp.dtype, np.uint8)
        self.assertEqual(int(inp.min()), 255)

    def test_unsupported_shape_and_multiple_tensor_outputs_rejected_early(self):
        cases = (
            ('gray.tflite', {'shape': (1, 120, 160, 1)}, 'input shape'),
            ('dynamic.tflite', {'shape': (1, -1, 160, 3)}, 'input shape'),
            ('batch.tflite', {'shape': (2, 120, 160, 3)}, 'input shape'),
            ('many.tflite', {'shape': (1, 8000, 8000, 3)}, 'too large'),
            ('heads.tflite', {'outputs': 2}, 'one [steering, throttle]'),
            ('wrong-out.tflite', {'output_shape': (1, 3)}, 'output shape'),
            ('input16.tflite', {'input_dtype': np.int16}, 'dtype'),
            ('quant-bad.tflite', {'input_dtype': np.uint8}, 'quantization'),
        )
        for name, config, error in cases:
            with self.subTest(name=name):
                self.add_model(name, **config)
                ok, message = self.svc.load_model(name)
                self.assertFalse(ok)
                self.assertIn(error, message)
                self.assertEqual(self.svc.get_active_name(), 'none')

    def test_failed_replacement_preserves_previous_model(self):
        self.add_model('good.tflite', shape=(1, 120, 160, 3))
        self.add_model('bad.tflite', bad_invoke=True)
        self.assertTrue(self.svc.load_model('good.tflite')[0])
        old_interpreter = self.svc.interpreter
        ok, message = self.svc.load_model('bad.tflite')
        self.assertFalse(ok)
        self.assertIn('inference failed', message)
        self.assertIs(self.svc.interpreter, old_interpreter)
        self.assertEqual(self.svc.get_active_name(), 'good.tflite')
        self.assertIsNotNone(self.svc.predict_uv_from_frame(np.zeros((2, 2, 3), np.uint8)))

    def test_preflight_rejects_nonfinite_outputs(self):
        self.add_model('nan.tflite', output=(float('nan'), .7))
        ok, message = self.svc.load_model('nan.tflite')
        self.assertFalse(ok)
        self.assertIn('non-finite', message)

    def test_nonfinite_runtime_output_does_not_become_motor_command(self):
        self.add_model('good.tflite')
        self.assertTrue(self.svc.load_model('good.tflite')[0])
        FakeInterpreter.instances[-1].config['output'] = (float('inf'), 0.6)
        self.assertIsNone(self.svc.predict_uv_from_frame(np.zeros((2,2,3), np.uint8)))

    def test_inference_without_active_model_returns_none(self):
        self.assertIsNone(self.svc.predict_uv_from_frame(np.zeros((1,1,3), np.uint8)))
        self.assertIsNone(self.svc.get_input_spec())

    def test_deleting_active_model_clears_cached_details(self):
        self.add_model('good.tflite')
        self.assertTrue(self.svc.load_model('good.tflite')[0])
        self.assertTrue(self.svc.delete_model('good.tflite')[0])
        self.assertIsNone(self.svc.get_input_spec())
        self.assertIsNone(self.svc.predict_uv_from_frame(np.zeros((2,2,3), np.uint8)))


class PerformanceInputParityTests(unittest.TestCase):
    def test_prepare_input_preserves_exact_float_pixels_and_source(self):
        rng = np.random.default_rng(17)
        frame = rng.integers(0, 256, (240, 426, 3), dtype=np.uint8)
        original = frame.copy()
        for size in ((160, 120), (426, 240)):
            actual = ModelService._prepare_input(None, frame, size)
            expected = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), size).astype(np.float32) / 255.0
            np.testing.assert_array_equal(actual, expected[None, ...])
            self.assertEqual(actual.dtype, np.float32)
            self.assertTrue(actual.flags.c_contiguous)
        np.testing.assert_array_equal(frame, original)


class PerformanceTensorReuseTests(unittest.TestCase):
    def test_same_dtype_input_reuses_owned_tensor_and_integer_parity(self):
        x = np.linspace(0, 1, 300, dtype=np.float32).reshape(1, 10, 10, 3)
        before = x.copy()
        self.assertIs(ModelService._quantize_if_needed(None, x, {"dtype": np.float32}), x)
        for dtype, zero in ((np.int8, -128), (np.uint8, 0)):
            scale = 1 / 255
            limits = np.iinfo(dtype)
            expected = np.clip(np.rint(x / scale + zero), limits.min, limits.max).astype(dtype)
            actual = ModelService._quantize_if_needed(None, x, {"dtype": dtype, "quantization": (scale, zero)})
            np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(x, before)


if __name__ == '__main__':
    unittest.main()
