from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import math
import threading
import unittest
from pisd.core.latency_metrics import RollingLatency


class FakeClock:
    def __init__(self):
        self.wall = 0.0
        self.cpu = 0.0
    def tick(self): return self.wall
    def cpu_tick(self): return self.cpu


class RollingLatencyTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.stats = RollingLatency(('capture', 'resize', 'inference', 'motor_apply', 'control_loop'), capacity=4,
                                    clock=self.clock.tick, cpu_clock=self.clock.cpu_tick)

    def test_empty_stages_are_absent(self):
        data = self.stats.snapshot()
        self.assertEqual(data['stages'], {})
        self.assertIsNone(data['process_cpu_percent'])
        self.assertEqual(data['window_capacity'], 4)

    def test_bounded_window_nearest_rank_percentiles(self):
        for ms in (1, 2, 3, 4, 9): self.stats.observe_ms('inference', ms)
        data = self.stats.snapshot()['stages']['inference']
        self.assertEqual(data, {'samples': 4, 'last_ms': 9.0, 'p50_ms': 3.0, 'p95_ms': 9.0})

    def test_fake_clock_elapsed_time(self):
        start = self.stats.start()
        self.clock.wall = 0.0125
        self.stats.observe_elapsed('capture', start)
        self.assertAlmostEqual(self.stats.snapshot()['stages']['capture']['last_ms'], 12.5)

    def test_cpu_sampled_only_after_one_second(self):
        self.clock.cpu = 0.4
        self.clock.wall = 0.4
        self.assertIsNone(self.stats.snapshot()['process_cpu_percent'])
        self.clock.cpu = 0.9
        self.clock.wall = 1.0
        self.assertEqual(self.stats.snapshot()['process_cpu_percent'], 90.0)
        self.clock.cpu = 1.0
        self.clock.wall = 1.5
        self.assertEqual(self.stats.snapshot()['process_cpu_percent'], 90.0)

    def test_multi_core_cpu_allowed(self):
        self.clock.cpu, self.clock.wall = 2.0, 1.0
        self.assertEqual(self.stats.snapshot()['process_cpu_percent'], 200.0)

    def test_drop_nonfinite_and_negative_timings(self):
        for value in (float('nan'), float('inf'), -1.0): self.stats.observe_ms('inference', value)
        self.assertEqual(self.stats.snapshot()['stages'], {})

    def test_known_event_counters(self):
        self.stats.count('stale_frames')
        self.stats.count('dropped_frames', 3)
        self.assertEqual(self.stats.snapshot()['counters']['dropped_frames'], 3)
        self.assertEqual(self.stats.snapshot()['counters']['stale_frames'], 1)

    def test_unknown_keys_rejected_and_invalid_increments(self):
        with self.assertRaises(KeyError): self.stats.observe_ms('fake', 100)
        with self.assertRaises(KeyError): self.stats.count('fake')
        with self.assertRaises(ValueError): self.stats.count('dropped_frames', -1)
        with self.assertRaises(ValueError): self.stats.count('dropped_frames', True)

    def test_capacity_is_bounded(self):
        with self.assertRaises(ValueError): RollingLatency(('a',), capacity=0)
        with self.assertRaises(ValueError): RollingLatency(('a',), capacity=10000)
        with self.assertRaises(ValueError): RollingLatency(('a', 'a'))

    def test_concurrent_writer_and_reader(self):
        def write():
            for x in range(1000):
                self.stats.observe_ms('inference', x % 7)
                self.stats.count('inference_failures')
        threads = [threading.Thread(target=write) for _ in range(4)]
        for thread in threads: thread.start()
        for _ in range(20): self.stats.snapshot()
        for thread in threads: thread.join()
        report = self.stats.snapshot()
        self.assertEqual(report['stages']['inference']['samples'], 4)
        self.assertEqual(report['counters']['inference_failures'], 4000)


if __name__ == '__main__': unittest.main()
