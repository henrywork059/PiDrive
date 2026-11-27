import unittest
import numpy as np
from tools.benchmark_tflite_threads import compare


class Fake:
    def __init__(self, **kwargs):
        self.threads = kwargs.get('num_threads')
        if self.threads == 4:
            raise TypeError('unsupported threads')

    def allocate_tensors(self):
        pass

    def get_input_details(self):
        return [{'shape': [1, 2, 2, 3], 'dtype': np.float32, 'index': 0}]

    def get_output_details(self):
        return [{'shape': [1, 2], 'index': 1}]

    def set_tensor(self, index, value):
        self.value = value

    def invoke(self):
        pass

    def get_tensor(self, index):
        return np.array([[self.value.mean(), float(self.threads == 2)]], dtype=np.float32)


class ThreadBenchmarkTests(unittest.TestCase):
    def test_parity_and_unsupported_are_distinct(self):
        inputs = np.arange(24, dtype=np.float32).reshape(2, 2, 2, 3)
        report = compare(Fake, 'fixture.tflite', inputs, rounds=2, warmup=1, invocations=3)
        summary = {item['threads']: item for item in report['summary']}
        self.assertTrue(summary[None]['exact_output_parity'])
        self.assertTrue(summary[1]['exact_output_parity'])
        self.assertTrue(summary[2]['complete'])
        self.assertFalse(summary[2]['exact_output_parity'])
        self.assertFalse(summary[4]['complete'])
        self.assertFalse(report['deployment_authorized'])
        for row in report['rounds']:
            self.assertEqual(set(row['order']), {None, 1, 2, 4})

    def test_bad_input_and_thread_settings_rejected(self):
        with self.assertRaises(ValueError):
            compare(Fake, 'fixture.tflite', np.zeros((2, 2, 2, 3), dtype=np.uint8), rounds=1)
        with self.assertRaises(ValueError):
            compare(Fake, 'fixture.tflite', np.zeros((2, 2, 2, 3), dtype=np.float32), thread_counts=(0,))


if __name__ == '__main__':
    unittest.main()
