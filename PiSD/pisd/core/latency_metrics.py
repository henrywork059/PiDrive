"""Bounded, low-overhead process-local pipeline timing summaries.

No background sampler, dependency, I/O, or per-frame sorting. All duration
samples use a monotonic clock; percentiles are calculated only on inspection.
"""
from __future__ import annotations

from collections import deque
import math
import threading
import time
from typing import Callable


class RollingLatency:
    def __init__(
        self,
        stages: tuple[str, ...],
        *,
        capacity: int = 120,
        clock: Callable[[], float] = time.perf_counter,
        cpu_clock: Callable[[], float] = time.process_time,
    ) -> None:
        if not stages or len(set(stages)) != len(stages):
            raise ValueError('Unique nonempty stages are required.')
        if not 1 <= capacity <= 1000:
            raise ValueError('Capacity must be between 1 and 1000.')
        self._samples = {key: deque(maxlen=capacity) for key in stages}
        self._counts = {'dropped_frames': 0, 'stale_frames': 0, 'reused_predictions': 0, 'inference_failures': 0}
        self._lock = threading.Lock()
        self._clock = clock
        self._cpu_clock = cpu_clock
        self._cpu_at = clock()
        self._cpu_work = cpu_clock()
        self._cpu_pct: float | None = None
        self._capacity = capacity

    def start(self) -> float:
        return self._clock()

    def observe_elapsed(self, stage: str, started: float) -> None:
        self.observe_ms(stage, (self._clock() - started) * 1000.0)

    def observe_ms(self, stage: str, duration_ms: float) -> None:
        if stage not in self._samples:
            raise KeyError(f'Unknown latency stage: {stage}')
        value = float(duration_ms)
        if not math.isfinite(value) or value < 0:
            return  # A broken timing source must not poison reporting.
        with self._lock:
            self._samples[stage].append(value)

    def count(self, event: str, amount: int = 1) -> None:
        if event not in self._counts:
            raise KeyError(f'Unknown counter: {event}')
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError('Count increment must be a nonnegative integer.')
        with self._lock:
            self._counts[event] += amount

    @staticmethod
    def _nearest_rank(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]

    def snapshot(self) -> dict:
        # This is process-wide CPU utilization, not a per-core normalized value.
        now, cpu = self._clock(), self._cpu_clock()
        with self._lock:
            wall_delta, cpu_delta = now - self._cpu_at, cpu - self._cpu_work
            if wall_delta >= 1.0 and cpu_delta >= 0:
                self._cpu_pct = round(100 * cpu_delta / wall_delta, 2)
                self._cpu_at, self._cpu_work = now, cpu
            stages = {}
            for key, samples in self._samples.items():
                if not samples:
                    continue  # An unmeasured stage must not be labelled as zero latency.
                values = list(samples)
                stages[key] = {
                    'samples': len(values),
                    'last_ms': round(values[-1], 3),
                    'p50_ms': round(self._nearest_rank(values, 0.50), 3),
                    'p95_ms': round(self._nearest_rank(values, 0.95), 3),
                }
            return {
                'window_capacity': self._capacity,
                'stages': stages,
                'counters': dict(self._counts),
                'process_cpu_percent': self._cpu_pct,
                'cpu_note': 'Process CPU time / elapsed time; may exceed 100% on multi-core machines.',
            }
