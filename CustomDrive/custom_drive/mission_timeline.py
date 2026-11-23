"""Read-only Mission 1 transition history derived from real runtime phases (R33).

This module has no access to motors, camera, network, config or arm controls.
Only phases actually observed by the running Mission 1 server are included.
"""
from __future__ import annotations

import copy
import threading
from typing import Any

# The Mission 1 state machine uses these existing phase strings. Labels are
# descriptive, not a prescriptive route with compulsory stages.
PHASE_STEPS: dict[str, tuple[str, str, int | None]] = {
    'route_pending': ('route', 'Route', 10),
    'start_route': ('route', 'Route', 10),
    'camera_boot': ('camera', 'Camera startup', 20),
    'model_boot': ('model', 'Model loading', 30),
    'ai_wait_frame': ('wait_frame', 'Waiting for frame', None),
    'ai_pickup_search': ('pickup_search', 'Search · pickup', 40),
    'ai_pickup_track': ('pickup_align', 'Align · pickup', 50),
    'ai_pickup_stop': ('grip', 'Grip · stop / settle', 60),
    'ai_pickup_grip': ('grip', 'Grip · pose', 60),
    'ai_pickup_lift': ('lift', 'Grip · lift', 70),
    'ai_dropoff_search': ('transport', 'Transport · find drop-off', 80),
    'ai_dropoff_track': ('dropoff', 'Drop-off · align', 90),
    'ai_dropoff_stop': ('release', 'Release · stop / settle', 100),
    'ai_dropoff_release': ('release', 'Release · pose', 100),
    'ai_reverse_reset': ('reset', 'Return · reverse / reset', 110),
}


class MissionProgressTimeline:
    """Bounded, per-session stage observations; never advances the mission."""

    def __init__(self, *, history_limit: int = 30) -> None:
        self._lock = threading.RLock()
        self._history_limit = max(8, min(80, int(history_limit)))
        self.reset('')

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._session_id = str(session_id or '')
            self._history: list[dict[str, Any]] = []
            self._current: dict[str, Any] | None = None
            self._last_completed: dict[str, Any] | None = None
            self._last_failure: dict[str, Any] | None = None
            self._cycle = 0

    def observe(
        self,
        phase: Any,
        mission_state: Any = '',
        *,
        outcome: Any = 'running',
        failure_reason: Any = '',
        failure_stage: Any = '',
        last_error: Any = '',
    ) -> None:
        phase = str(phase or '')
        mission_state = str(mission_state or '')
        outcome = str(outcome or '').lower()
        with self._lock:
            if not self._session_id:
                return

            if outcome == 'failed' or phase == 'failed':
                if self._current and self._history:
                    self._history[-1]['state'] = 'failed'
                if self._last_failure is None:
                    self._last_failure = {
                        'reason': str(failure_reason or 'runtime_error'),
                        'stage': str(failure_stage or mission_state or phase),
                        'message': str(last_error or ''),
                    }
                return

            if outcome == 'stopped' or phase == 'stopped':
                if self._current and self._history and self._history[-1]['state'] == 'current':
                    self._history[-1]['state'] = 'interrupted'
                return

            if outcome == 'complete' or phase == 'complete':
                if self._current and self._history:
                    self._history[-1]['state'] = 'completed'
                    self._last_completed = copy.deepcopy(self._history[-1])
                return

            spec = PHASE_STEPS.get(phase)
            if spec is None:
                return
            key, label, rank = spec
            if self._current and self._current['id'] == key:
                # A grip/release pose can change from stop/settle to pose without
                # changing the major stage. Keep the actual current subphase.
                self._current['label'] = label
                self._current['phase'] = phase
                self._current['mission_state'] = mission_state
                if self._history:
                    self._history[-1].update(self._current)
                return

            previous = self._current
            if previous is not None and self._history:
                old_rank = PHASE_STEPS.get(previous['phase'], ('', '', None))[2]
                if rank is not None and old_rank is not None and rank > old_rank:
                    self._history[-1]['state'] = 'completed'
                    self._last_completed = copy.deepcopy(self._history[-1])
                else:
                    # Pauses, lost-frame recovery and backwards loops must not
                    # manufacture a successful completed stage.
                    self._history[-1]['state'] = 'left'

            if key == 'pickup_search' and (self._cycle == 0 or
                    (previous and previous['id'] in {'reset', 'release'})):
                self._cycle += 1
            entry = {
                'id': key, 'label': label, 'phase': phase,
                'mission_state': mission_state, 'cycle': self._cycle,
                'state': 'current',
            }
            self._current = entry.copy()
            self._history.append(entry)
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit:]

    def snapshot(self, *, outcome: Any = 'idle', detail: Any = '',
                 arm_sequence: Any = None) -> dict[str, Any]:
        with self._lock:
            return {
                'schema_version': 1,
                'session_id': self._session_id,
                'outcome': str(outcome or 'idle'),
                'current_step': copy.deepcopy(self._current),
                'last_completed_step': copy.deepcopy(self._last_completed),
                'last_failure': copy.deepcopy(self._last_failure),
                'recent_steps': copy.deepcopy(self._history[-12:]),
                'detail': str(detail or ''),
                'arm_sequence': copy.deepcopy(arm_sequence) if isinstance(arm_sequence, dict) else {},
            }
