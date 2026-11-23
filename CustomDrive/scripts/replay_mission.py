#!/usr/bin/env python3
"""Deterministic CustomDrive mission replay: synthetic perception, fake robot only.

No GPIO, camera, arm service, web app or hardware runner is constructed.
The confidence field is detector confidence, NOT confidence in steering output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAX_STEPS = 5000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f'{name} cannot be boolean')
    num = float(value)
    if not math.isfinite(num):
        raise ValueError(f'{name} must be finite')
    return num


def parse_detection(item: dict[str, Any]):
    from custom_drive.models import BoundingBox, Detection

    if not isinstance(item, dict):
        raise ValueError('Detection must be an object')
    box = item.get('box')
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError('Detection box must be [x1,y1,x2,y2]')
    x1, y1, x2, y2 = [finite(x, 'box coordinate') for x in box]
    if x2 <= x1 or y2 <= y1:
        raise ValueError('Detection box must have positive size')
    conf = finite(item['confidence'], 'detection confidence')
    if conf < 0 or conf > 1:
        raise ValueError('Detection confidence must be [0,1]')
    label = str(item.get('label') or '').strip()
    if not label:
        raise ValueError('Detection label missing')
    return Detection(label=label, confidence=conf,
                     box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2))


def replay(fixture: Path, *, max_steering_mae: float | None = None) -> dict[str, Any]:
    # Use production mission-controller math with a time-injected fake robot.
    from custom_drive.config import MissionConfig
    from custom_drive.fake_robot import FakeRobot
    from custom_drive.mission_controller import MissionController
    from custom_drive.models import FramePerception

    class ReplayRobot(FakeRobot):
        def __init__(self):
            super().__init__()
            self.virtual_time = 0.0

        def now(self) -> float:
            return self.virtual_time

    source = json.loads(fixture.read_text(encoding='utf-8'))
    if not isinstance(source, dict) or source.get('schema_version') != 1:
        raise ValueError('Fixture requires schema_version: 1')
    frames = source.get('frames')
    if not isinstance(frames, list) or not (1 <= len(frames) <= MAX_STEPS):
        raise ValueError('Fixture frames must be a nonempty bounded list')
    conf = source.get('config', {})
    if not isinstance(conf, dict):
        raise ValueError('Config overrides must be an object')
    # Explicit allowlist: never access saved runtime settings in this replay.
    allowed = {'target_label', 'drop_zone_label', 'min_confidence', 'search_timeout_s',
               'max_retries_per_stage', 'center_hold_frames', 'max_cycles', 'enable_repeat'}
    if set(conf) - allowed:
        raise ValueError(f'Unknown replay config overrides: {sorted(set(conf) - allowed)}')
    config = MissionConfig()
    for k, v in conf.items():
        if isinstance(getattr(config, k), bool):
            if type(v) is not bool:
                raise ValueError(f'{k} must be boolean')
            setattr(config, k, v)
        elif isinstance(getattr(config, k), int):
            value = finite(v, k)
            if value != int(value) or value < 0 or value > 10000:
                raise ValueError(f'{k} invalid integer')
            setattr(config, k, int(value))
        elif isinstance(getattr(config, k), float):
            setattr(config, k, finite(v, k))
        else:
            setattr(config, k, str(v))
    robot = ReplayRobot()
    controller = MissionController(robot=robot, config=config)
    controller.start()
    results = []
    failures = []
    abs_errors: list[float] = []
    previous = -math.inf
    terminal_failure_reported = False
    for i, raw in enumerate(frames):
        if not isinstance(raw, dict):
            raise ValueError(f'Frame {i} must be object')
        at = finite(raw['at_s'], 'virtual time')
        if at < 0 or at <= previous:
            raise ValueError('Frame times must be strictly increasing and nonnegative')
        previous = at
        robot.virtual_time = at
        width = int(finite(raw.get('width', 640), 'width'))
        height = int(finite(raw.get('height', 360), 'height'))
        if width <= 0 or height <= 0 or width > 8192 or height > 8192:
            raise ValueError('Invalid synthetic frame dimensions')
        detections = [parse_detection(d) for d in raw.get('detections', [])]
        snapshot = controller.update(FramePerception(frame_width=width, frame_height=height,
                                                     detections=detections, timestamp=at))
        command = snapshot.last_command
        steering = finite(command.steering, 'controller steering')
        throttle = finite(command.throttle, 'controller throttle')
        # In the fake robot, 'drive' is only an in-memory log entry.
        row: dict[str, Any] = {
            'index': i, 'virtual_time_s': at, 'state': snapshot.state,
            'predicted_steering': steering, 'predicted_throttle': throttle,
            'detection_confidence': max((d.confidence for d in detections), default=None),
            'steering_confidence': None, 'command_note': str(command.note),
            'mock_motor_steering': robot.last_command.steering,
            'mock_motor_throttle': robot.last_command.throttle,
        }
        if 'label_steering' in raw:
            label = finite(raw['label_steering'], 'label steering')
            if not (-1 <= label <= 1):
                raise ValueError('Steering label must be [-1,1]')
            error = abs(steering - label)
            abs_errors.append(error)
            row.update({'label_steering': label, 'absolute_error': round(error, 8)})
        if 'expected_state' in raw and snapshot.state != raw['expected_state']:
            failures.append({'index': i, 'virtual_time_s': at, 'event': 'state_mismatch',
                             'expected': raw['expected_state'], 'actual': snapshot.state})
        if snapshot.state == 'failed' and not terminal_failure_reported:
            failures.append({'index': i, 'virtual_time_s': at, 'event': 'mission_failed', 'detail': snapshot.detail})
            terminal_failure_reported = True
        results.append(row)
    if max_steering_mae is not None and (not math.isfinite(max_steering_mae) or max_steering_mae < 0):
        raise ValueError('Invalid MAE threshold')
    return {
        'schema_version': 1, 'component': 'CustomDrive', 'mode': 'synthetic_mission_replay',
        'read_only': True, 'hardware_initialized': False, 'motor_adapter': 'FakeRobot',
        'input': {'fixture': str(fixture), 'fixture_sha256': sha256(fixture),
                  'controller_source_sha256': sha256(ROOT / 'custom_drive/mission_controller.py'),
                  'model': None, 'model_sha256': None},
        'total_frames': len(frames), 'labelled_frames': len(abs_errors),
        'steering_mae': round(sum(abs_errors) / len(abs_errors), 8) if abs_errors else None,
        'final_state': controller.state.value,
        'frames': results, 'failure_events': failures,
        'regression_failed': bool(failures or (max_steering_mae is not None and (
            not abs_errors or sum(abs_errors) / len(abs_errors) > max_steering_mae))),
    }


def write_report(report: dict[str, Any], output: Path, fixture: Path) -> None:
    if output.resolve() == fixture.resolve():
        raise ValueError('Report cannot overwrite the fixture')
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=ROOT / 'scripts/fixtures/mission_replay.json')
    parser.add_argument('--report', type=Path, help='Optional new report path (refuses overwrite)')
    parser.add_argument('--max-steering-mae', type=float, default=None)
    args = parser.parse_args(argv)
    try:
        report = replay(args.fixture, max_steering_mae=args.max_steering_mae)
        if args.report:
            write_report(report, args.report, args.fixture)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 2 if report['regression_failed'] else 0
    except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f'Replay refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
