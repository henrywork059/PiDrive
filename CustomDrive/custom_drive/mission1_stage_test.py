from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RouteLeg
from .models import DriveCommand
from .picar_bridge import PiCarRobotBridge
from .project_paths import CONFIG_DIR, ensure_piserver_import_paths
from .route_script import TimedRouteFollower
from .runtime_settings import load_settings

CONFIG_PATH = CONFIG_DIR / 'mission1_stage_test.json'

_ALLOWED_ACTIONS = ('forward', 'turn-right', 'turn-left')


@dataclass(slots=True)
class RouteStepSpec:
    action: str
    duration_s: float


@dataclass(slots=True)
class Mission1StageTestConfig:
    enabled: bool = True
    mode: str = 'sim'
    tick_s: float = 0.05
    forward_1_duration_s: float = 6.0
    turn_right_duration_s: float = 5.0
    forward_2_duration_s: float = 6.0
    forward_throttle: float = 0.28
    forward_steering: float = 0.0
    turn_right_throttle: float = 0.22
    turn_right_steering: float = -0.65
    settle_stop_s: float = 0.25
    route_steps: list[RouteStepSpec] = field(default_factory=list)


class AppendRouteStepAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        action_name = str(option_string or '').lstrip('-').strip().lower()
        if action_name not in _ALLOWED_ACTIONS:
            raise argparse.ArgumentError(self, f'Unsupported route action: {action_name}')
        try:
            duration_s = float(values)
        except Exception as exc:  # pragma: no cover - argparse also handles types; this is a guard.
            raise argparse.ArgumentError(self, f'Invalid duration for {action_name}: {values!r}') from exc
        route_steps = list(getattr(namespace, 'route_steps_cli', []) or [])
        route_steps.append(RouteStepSpec(action=action_name, duration_s=duration_s))
        setattr(namespace, 'route_steps_cli', route_steps)


def _clamp_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        result = float(value)
    except Exception:
        result = float(default)
    return max(float(low), min(float(high), result))


def _clamp_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {'1', 'true', 'yes', 'on'}:
            return True
        if text in {'0', 'false', 'no', 'off'}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _normalize_route_steps(raw_steps: Any) -> list[RouteStepSpec]:
    normalized: list[RouteStepSpec] = []
    if not isinstance(raw_steps, list):
        return normalized
    for item in raw_steps:
        if not isinstance(item, dict):
            continue
        action = str(item.get('action', '')).strip().lower()
        if action not in _ALLOWED_ACTIONS:
            continue
        duration_s = _clamp_float(item.get('duration_s'), 0.0, 0.05, 30.0)
        normalized.append(RouteStepSpec(action=action, duration_s=duration_s))
    return normalized


def load_config(path: Path = CONFIG_PATH) -> Mission1StageTestConfig:
    cfg = Mission1StageTestConfig()
    if not path.exists():
        return cfg
    raw = json.loads(path.read_text(encoding='utf-8'))
    for key in cfg.__dataclass_fields__:
        if key == 'route_steps':
            continue
        if key in raw:
            setattr(cfg, key, raw[key])

    cfg.enabled = _clamp_bool(cfg.enabled, True)
    cfg.mode = str(cfg.mode or 'sim').strip().lower() or 'sim'
    if cfg.mode not in {'sim', 'live'}:
        cfg.mode = 'sim'
    cfg.tick_s = _clamp_float(cfg.tick_s, 0.05, 0.02, 1.0)
    cfg.forward_1_duration_s = _clamp_float(cfg.forward_1_duration_s, 6.0, 0.05, 30.0)
    cfg.turn_right_duration_s = _clamp_float(cfg.turn_right_duration_s, 5.0, 0.05, 30.0)
    cfg.forward_2_duration_s = _clamp_float(cfg.forward_2_duration_s, 6.0, 0.05, 30.0)
    cfg.forward_throttle = _clamp_float(cfg.forward_throttle, 0.28, -1.0, 1.0)
    cfg.forward_steering = _clamp_float(cfg.forward_steering, 0.0, -1.0, 1.0)
    cfg.turn_right_throttle = _clamp_float(cfg.turn_right_throttle, 0.22, -1.0, 1.0)
    cfg.turn_right_steering = _clamp_float(cfg.turn_right_steering, -0.65, -1.0, 1.0)
    cfg.settle_stop_s = _clamp_float(cfg.settle_stop_s, 0.25, 0.0, 5.0)
    cfg.route_steps = _normalize_route_steps(raw.get('route_steps'))
    return cfg


def save_config(cfg: Mission1StageTestConfig, path: Path = CONFIG_PATH) -> None:
    payload = {key: getattr(cfg, key) for key in cfg.__dataclass_fields__ if key != 'route_steps'}
    payload['route_steps'] = [
        {'action': step.action, 'duration_s': float(step.duration_s)}
        for step in cfg.route_steps
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Mission 1 stage test runner with configurable leg timings and free-form route steps.', allow_abbrev=False)
    parser.add_argument('--mode', choices=['sim', 'live'], help='Override mode from config/mission1_stage_test.json')
    parser.add_argument('--tick', type=float, help='Loop interval in seconds')
    parser.add_argument('--forward-throttle', type=float, help='Throttle used for forward steps')
    parser.add_argument('--turn-throttle', type=float, help='Throttle used during turn steps')
    parser.add_argument('--turn-steering', type=float, help='Steering magnitude used during turn steps')
    parser.add_argument('--forward-1', dest='forward_1_duration_s', type=float, help='First forward-leg duration in seconds')
    parser.add_argument('--turn-right-time', dest='turn_right_duration_s', type=float, help='Right-turn-leg duration in seconds for the legacy 3-leg route')
    parser.add_argument('--forward-2', dest='forward_2_duration_s', type=float, help='Second forward-leg duration in seconds')
    parser.add_argument('--settle-stop', type=float, help='Extra stop time after the route finishes')
    parser.add_argument('--forward', metavar='SECONDS', action=AppendRouteStepAction, help='Append a forward step to the route in the exact CLI order used')
    parser.add_argument('--turn-right', metavar='SECONDS', action=AppendRouteStepAction, help='Append a right-turn step to the route in the exact CLI order used')
    parser.add_argument('--turn-left', metavar='SECONDS', action=AppendRouteStepAction, help='Append a left-turn step to the route in the exact CLI order used')
    parser.add_argument('--save-config', action='store_true', help='Save the resolved settings back into config/mission1_stage_test.json and exit')
    parser.add_argument('--run-and-save', action='store_true', help='Save the resolved settings to config/mission1_stage_test.json before running')
    parser.add_argument('--info', action='store_true', help='Print the resolved route settings and exit')
    return parser


def apply_cli_overrides(cfg: Mission1StageTestConfig, args: argparse.Namespace) -> Mission1StageTestConfig:
    if args.mode is not None:
        cfg.mode = str(args.mode).strip().lower() or cfg.mode
    if args.tick is not None:
        cfg.tick_s = _clamp_float(args.tick, cfg.tick_s, 0.02, 1.0)
    if args.forward_throttle is not None:
        cfg.forward_throttle = _clamp_float(args.forward_throttle, cfg.forward_throttle, -1.0, 1.0)
    if args.turn_throttle is not None:
        cfg.turn_right_throttle = _clamp_float(args.turn_throttle, cfg.turn_right_throttle, -1.0, 1.0)
    if args.turn_steering is not None:
        cfg.turn_right_steering = _clamp_float(args.turn_steering, cfg.turn_right_steering, -1.0, 1.0)
    if args.forward_1_duration_s is not None:
        cfg.forward_1_duration_s = _clamp_float(args.forward_1_duration_s, cfg.forward_1_duration_s, 0.05, 30.0)
    if args.turn_right_duration_s is not None:
        cfg.turn_right_duration_s = _clamp_float(args.turn_right_duration_s, cfg.turn_right_duration_s, 0.05, 30.0)
    if args.forward_2_duration_s is not None:
        cfg.forward_2_duration_s = _clamp_float(args.forward_2_duration_s, cfg.forward_2_duration_s, 0.05, 30.0)
    if args.settle_stop is not None:
        cfg.settle_stop_s = _clamp_float(args.settle_stop, cfg.settle_stop_s, 0.0, 5.0)
    route_steps_cli = list(getattr(args, 'route_steps_cli', []) or [])
    legacy_forward_args_used = args.forward_1_duration_s is not None or args.forward_2_duration_s is not None
    compat_middle_turn_override = (
        legacy_forward_args_used
        and args.turn_right_duration_s is None
        and len(route_steps_cli) == 1
        and route_steps_cli[0].action == 'turn-right'
    )
    if compat_middle_turn_override:
        cfg.turn_right_duration_s = _clamp_float(route_steps_cli[0].duration_s, cfg.turn_right_duration_s, 0.05, 30.0)
        route_steps_cli = []

    legacy_fixed_requested = (
        args.forward_1_duration_s is not None
        or args.turn_right_duration_s is not None
        or args.forward_2_duration_s is not None
        or compat_middle_turn_override
    )
    if route_steps_cli:
        cfg.route_steps = [
            RouteStepSpec(action=step.action, duration_s=_clamp_float(step.duration_s, step.duration_s, 0.05, 30.0))
            for step in route_steps_cli
        ]
    elif legacy_fixed_requested:
        cfg.route_steps = []
    return cfg


def _route_steps_from_legacy_timings(cfg: Mission1StageTestConfig) -> list[RouteStepSpec]:
    return [
        RouteStepSpec(action='forward', duration_s=cfg.forward_1_duration_s),
        RouteStepSpec(action='turn-right', duration_s=cfg.turn_right_duration_s),
        RouteStepSpec(action='forward', duration_s=cfg.forward_2_duration_s),
    ]


def get_effective_route_steps(cfg: Mission1StageTestConfig) -> list[RouteStepSpec]:
    if cfg.route_steps:
        return [RouteStepSpec(action=step.action, duration_s=step.duration_s) for step in cfg.route_steps]
    return _route_steps_from_legacy_timings(cfg)


def build_route(cfg: Mission1StageTestConfig) -> list[RouteLeg]:
    route_steps = get_effective_route_steps(cfg)
    route: list[RouteLeg] = []
    for index, step in enumerate(route_steps, start=1):
        action = step.action
        if action == 'forward':
            command = DriveCommand(
                steering=cfg.forward_steering,
                throttle=cfg.forward_throttle,
                note=f'mission1 test: forward step {index}',
            )
        elif action == 'turn-right':
            command = DriveCommand(
                steering=cfg.turn_right_steering,
                throttle=cfg.turn_right_throttle,
                note=f'mission1 test: turn right step {index}',
            )
        elif action == 'turn-left':
            command = DriveCommand(
                steering=-cfg.turn_right_steering,
                throttle=cfg.turn_right_throttle,
                note=f'mission1 test: turn left step {index}',
            )
        else:  # pragma: no cover - guarded earlier; kept defensive for future extensions.
            continue
        route.append(RouteLeg(f'step_{index:02d}_{action.replace('-', '_')}', step.duration_s, command))
    return route


class _SimMotor:
    def update(self, steering: float, throttle: float, steer_mix: float = 0.75):
        left = float(throttle) + float(steering) * float(steer_mix)
        right = float(throttle) - float(steering) * float(steer_mix)
        return left, right

    def stop(self) -> None:
        return None


class _LiveBridgeContext:
    def __init__(self):
        ensure_piserver_import_paths()
        from piserver.services.motor_service import MotorService  # noqa: WPS433

        self.motor_service = MotorService()
        settings = load_settings()
        motor_cfg = settings.get('motor') or {}
        self.motor_service.apply_settings(motor_cfg)
        runtime_cfg = settings.get('runtime') or {}
        self.bridge = PiCarRobotBridge(
            motor=self.motor_service,
            arm=None,
            mode_name='custom_drive_mission1_test',
            steer_mix=float(runtime_cfg.get('steer_mix', 0.75)),
            allow_virtual_grab_without_arm=True,
        )

    def close(self) -> None:
        try:
            self.bridge.stop('mission1 stage test closed')
        except Exception:
            pass
        try:
            self.motor_service.close()
        except Exception:
            pass


class _SimBridgeContext:
    def __init__(self):
        self.motor_service = _SimMotor()
        self.bridge = PiCarRobotBridge(
            motor=self.motor_service,
            arm=None,
            mode_name='custom_drive_mission1_test_sim',
            steer_mix=0.75,
            allow_virtual_grab_without_arm=True,
        )

    def close(self) -> None:
        self.bridge.stop('mission1 sim test closed')


def make_bridge_context(mode: str):
    if mode == 'live':
        return _LiveBridgeContext()
    return _SimBridgeContext()


def format_route_sequence(cfg: Mission1StageTestConfig) -> str:
    parts: list[str] = []
    for step in get_effective_route_steps(cfg):
        label = step.action.replace('-', ' ')
        parts.append(f'{label} {step.duration_s:.2f}s')
    return ' -> '.join(parts)


def print_config_summary(cfg: Mission1StageTestConfig) -> None:
    route = build_route(cfg)
    total_time = sum(max(0.0, float(leg.duration_s)) for leg in route)
    print('Mission 1 stage test configuration')
    print(f'  config file          : {CONFIG_PATH}')
    print(f'  mode                 : {cfg.mode}')
    print(f'  tick_s               : {cfg.tick_s:.2f}')
    print(f'  settle_stop_s        : {cfg.settle_stop_s:.2f}')
    print(f'  forward_throttle     : {cfg.forward_throttle:+.2f}')
    print(f'  forward_steering     : {cfg.forward_steering:+.2f}')
    print(f'  turn_right_throttle  : {cfg.turn_right_throttle:+.2f}')
    print(f'  turn_right_steering  : {cfg.turn_right_steering:+.2f}')
    print(f'  route total          : {total_time:.2f}s')
    print(f'  route sequence       : {format_route_sequence(cfg)}')
    for index, leg in enumerate(route, start=1):
        print(
            f'  leg {index}: {leg.name} | duration={leg.duration_s:.2f}s '
            f'| steering={leg.command.steering:+.2f} | throttle={leg.command.throttle:+.2f}'
        )


def run_route(cfg: Mission1StageTestConfig) -> int:
    if not cfg.enabled:
        raise RuntimeError('Mission 1 stage test is disabled in config/mission1_stage_test.json. Set enabled=true before running it.')

    route_name = 'mission1_stage_test'
    route = build_route(cfg)
    if not route:
        raise RuntimeError('No route steps were resolved. Add route_steps in config or pass CLI actions like --forward 5 --turn-right 5.')
    follower = TimedRouteFollower({route_name: route})
    context = make_bridge_context(cfg.mode)
    bridge = context.bridge
    tick = max(0.02, float(cfg.tick_s))
    active_leg = None

    print('=== Mission 1 stage test started ===')
    print_config_summary(cfg)
    print(f'Testing sequence: {format_route_sequence(cfg)}')
    try:
        follower.start(route_name, bridge.now())
        while True:
            done, cmd, leg = follower.update(bridge.now())
            if done:
                bridge.stop('mission1 stage route complete')
                if cfg.settle_stop_s > 0:
                    time.sleep(cfg.settle_stop_s)
                print('Route complete. Motors stopped.')
                break

            if leg != active_leg:
                active_leg = leg
                print(f'\n[LEG] {active_leg} | steering={cmd.steering:+.2f} throttle={cmd.throttle:+.2f} | note={cmd.note}')
            bridge.set_drive(cmd.steering, cmd.throttle, note=cmd.note)
            if bridge.last_error:
                raise RuntimeError(f'Motor command failed: {bridge.last_error}')
            time.sleep(tick)

        print('\nRecent bridge history:')
        for entry in bridge.history[-12:]:
            print(f'  [{entry.timestamp:.2f}s] {entry.action}: {entry.detail}')
        return 0
    finally:
        context.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        cfg = apply_cli_overrides(load_config(), args)
        if args.save_config:
            save_config(cfg)
            print_config_summary(cfg)
            print(f'\nSaved updated stage-test config to: {CONFIG_PATH}')
            return 0
        if args.run_and_save:
            save_config(cfg)
            print(f'Saved updated stage-test config to: {CONFIG_PATH}')
        if args.info:
            print_config_summary(cfg)
            return 0
        return run_route(cfg)
    except KeyboardInterrupt:
        print('Interrupted by user.')
        return 130
    except Exception as exc:
        print('Mission 1 stage test failed:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
