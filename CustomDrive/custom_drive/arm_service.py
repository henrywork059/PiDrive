from __future__ import annotations

import threading
import time
from typing import Any


class ArmService:
    """Simple Pi-side arm service for CustomDrive manual control.

    Supports:
    - PCA9685 + ServoKit backend when enabled.
    - Press-and-hold lift motion using a background worker.
    - Optional dual-servo lift output for matched arm height movement.
    - One-tap gripper actions for hold / release.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = {}
        self._kit = None
        self._move_thread: threading.Thread | None = None
        self._move_stop = threading.Event()
        self._move_lock = threading.RLock()
        self._move_direction = 0
        self._current_lift_angle = 0
        self.last_action = 'idle'
        self.last_error = ''
        self.last_message = 'Arm disabled.'
        self.last_action_at = 0.0
        self.backend = 'disabled'
        self.available = False
        self.enabled = False
        self.reload(config or {})

    def reload(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        self.stop_motion()
        cfg = dict(config or {})
        self._config = cfg
        self._kit = None
        self.last_error = ''
        self.last_message = 'Arm disabled.'
        self.last_action = 'idle'
        self.backend = str(cfg.get('backend', 'pca9685') or 'pca9685').strip().lower()
        self.enabled = bool(cfg.get('enabled', True))
        self.available = False
        self._current_lift_angle = self._angle('lift_down_angle', 115)

        if not self.enabled:
            self.backend = self.backend or 'disabled'
            self.last_message = 'Arm disabled in config.'
            return self.status()

        if self.backend != 'pca9685':
            self.last_error = f'Unsupported arm backend: {self.backend}'
            self.last_message = self.last_error
            return self.status()

        try:
            from adafruit_servokit import ServoKit  # type: ignore

            channels = int(cfg.get('channels', 16) or 16)
            address = int(cfg.get('i2c_address', 64) or 64)
            frequency = int(cfg.get('frequency_hz', 50) or 50)
            self._kit = ServoKit(channels=channels, address=address, frequency=frequency)
            self.available = True
            # Immediately assert the current hold angles so lift servos stay powered
            # after startup/reload and do not remain released from earlier tests.
            self._apply_lift_angle(self._current_lift_angle)
            self._apply_grip_angle(self._current_grip_angle)
            self.last_message = f'PCA9685 ready on 0x{address:02X}. Lift hold {self._current_lift_angle}°; grip hold {self._current_grip_angle}°.'
        except Exception as exc:  # pragma: no cover - hardware/env dependent
            self._kit = None
            self.available = False
            self.last_error = str(exc)
            self.last_message = f'Arm init failed: {exc}'
        return self.status()

    def shutdown(self) -> None:
        self.stop_motion()
        self._kit = None

    def _angle(self, key: str, default: int) -> int:
        value = self._config.get(key, default)
        try:
            value = int(value)
        except Exception:
            value = int(default)
        return max(0, min(180, value))

    def _channel(self, key: str, default: int) -> int:
        value = self._config.get(key, default)
        try:
            value = int(value)
        except Exception:
            value = int(default)
        return max(0, min(15, value))

    def _step_angle(self) -> int:
        return max(1, min(45, self._angle('lift_step_angle', 1)))

    def _step_interval_s(self) -> float:
        value = self._config.get('lift_step_interval_s', 0.1)
        try:
            value = float(value)
        except Exception:
            value = 0.1
        return max(0.02, min(1.0, value))

    def _secondary_enabled(self) -> bool:
        return bool(self._config.get('lift_secondary_enabled', True))

    def _secondary_multiplier(self) -> float:
        value = self._config.get('lift_secondary_multiplier', 1.0)
        try:
            value = float(value)
        except Exception:
            value = 1.0
        return max(0.0, min(4.0, value))

    def _secondary_channel(self) -> int:
        return self._channel('lift_channel_secondary', 1)

    def _set_servo_angle(self, channel: int, angle: int) -> None:
        if not self.enabled:
            raise RuntimeError('Arm is disabled in config.')
        if self._kit is None or not self.available:
            if self.last_error:
                raise RuntimeError(self.last_error)
            raise RuntimeError('Arm backend is not available.')
        self._kit.servo[channel].angle = angle

    def _apply_lift_angle(self, angle: int) -> None:
        primary = self._channel('lift_channel', 0)
        self._set_servo_angle(primary, angle)
        if self._secondary_enabled():
            secondary_channel = self._secondary_channel()
            if secondary_channel != primary:
                secondary_angle = int(round(max(0, min(180, angle * self._secondary_multiplier()))))
                self._set_servo_angle(secondary_channel, secondary_angle)

    def _target_for_direction(self, direction: int) -> int:
        up = self._angle('lift_up_angle', 40)
        down = self._angle('lift_down_angle', 115)
        return up if direction < 0 else down

    def _direction_sign(self, action_key: str) -> int:
        up = self._angle('lift_up_angle', 40)
        down = self._angle('lift_down_angle', 115)
        if action_key == 'up':
            return -1 if up <= down else 1
        return 1 if up <= down else -1

    def _move_loop(self) -> None:
        while not self._move_stop.is_set():
            with self._move_lock:
                direction = self._move_direction
            if direction == 0:
                break
            target = self._target_for_direction(direction)
            step = self._step_angle() * (1 if target > self._current_lift_angle else -1)
            next_angle = self._current_lift_angle + step
            if step > 0:
                next_angle = min(next_angle, target)
            else:
                next_angle = max(next_angle, target)
            try:
                self._apply_lift_angle(next_angle)
                self._current_lift_angle = next_angle
                self.last_action = 'up' if direction < 0 else 'down'
                self.last_action_at = time.time()
                self.last_error = ''
                self.last_message = f'Lift moving {self.last_action}: {self._current_lift_angle}°.'
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Arm move failed: {exc}'
                break
            if next_angle == target:
                break
            self._move_stop.wait(self._step_interval_s())
        with self._move_lock:
            self._move_direction = 0
            self._move_thread = None
        if not self.last_error:
            self.last_action = 'idle'

    def start_motion(self, action: str) -> tuple[bool, str]:
        action_key = str(action or '').strip().lower()
        if action_key not in {'up', 'down'}:
            return False, f'Unsupported lift motion: {action}'
        if not self.enabled:
            self.last_message = 'Arm disabled in config.'
            return False, self.last_message
        if not self.available:
            self.last_message = self.last_error or 'Arm backend is not available.'
            return False, self.last_message
        direction = self._direction_sign(action_key)
        self.stop_motion()
        with self._move_lock:
            self._move_direction = direction
            self._move_stop = threading.Event()
            self._move_thread = threading.Thread(target=self._move_loop, name='customdrive-arm-move', daemon=True)
            self._move_thread.start()
        self.last_action = action_key
        self.last_action_at = time.time()
        self.last_error = ''
        self.last_message = f'Lift {action_key} started.'
        return True, self.last_message

    def stop_motion(self) -> tuple[bool, str]:
        thread = None
        with self._move_lock:
            thread = self._move_thread
            self._move_direction = 0
            self._move_stop.set()
        if thread and thread.is_alive():
            thread.join(timeout=0.2)
        with self._move_lock:
            self._move_thread = None
        # Reassert the current lift angle so servo 0 remains powered/held instead
        # of appearing released after button release. This keeps the working gripper
        # path untouched and only stabilizes the lift channels.
        if self.enabled and self.available:
            try:
                self._apply_lift_angle(self._current_lift_angle)
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Lift hold failed: {exc}'
                return False, self.last_message
        self.last_action = 'idle'
        self.last_action_at = time.time()
        self.last_message = f'Lift stopped and held at {self._current_lift_angle}°.'
        return True, self.last_message

    def perform_action(self, action: str) -> tuple[bool, str]:
        action_key = str(action or '').strip().lower()
        action_key = {
            'open': 'release',
            'unclamp': 'release',
            'close': 'hold',
            'grab': 'hold',
            'clamp': 'hold',
            'lift': 'start_up',
            'raise_': 'start_up',
            'raise_up': 'start_up',
            'lower': 'start_down',
        }.get(action_key, action_key)

        if action_key in {'start_up', 'start-down', 'start_down'}:
            return self.start_motion('up' if action_key == 'start_up' else 'down')
        if action_key == 'stop':
            return self.stop_motion()
        if action_key == 'up':
            ok, msg = self.start_motion('up')
            if ok:
                time.sleep(0.08)
                self.stop_motion()
            return ok, msg
        if action_key == 'down':
            ok, msg = self.start_motion('down')
            if ok:
                time.sleep(0.08)
                self.stop_motion()
            return ok, msg

        mapping = {
            'hold': ('grip_channel', 'grip_hold_angle', 1, 70),
            'release': ('grip_channel', 'grip_release_angle', 1, 130),
        }
        if action_key not in mapping:
            message = f'Unknown arm action: {action}'
            self.last_error = message
            self.last_message = message
            return False, message

        channel_key, angle_key, default_channel, default_angle = mapping[action_key]
        channel = self._channel(channel_key, default_channel)
        angle = self._angle(angle_key, default_angle)
        try:
            self._set_servo_angle(channel, angle)
        except Exception as exc:
            self.last_error = str(exc)
            self.last_message = f'Arm action failed: {exc}'
            return False, self.last_message

        self.last_action = action_key
        self.last_error = ''
        self.last_action_at = time.time()
        self.last_message = f'Arm {action_key} sent on channel {channel} -> {angle}°.'
        return True, self.last_message

    def status(self) -> dict[str, Any]:
        return {
            'enabled': bool(self.enabled),
            'available': bool(self.available),
            'backend': self.backend,
            'last_action': self.last_action,
            'last_error': self.last_error,
            'last_message': self.last_message,
            'last_action_at': self.last_action_at,
            'lift_channel': self._channel('lift_channel', 0),
            'lift_channel_secondary': self._secondary_channel(),
            'lift_secondary_enabled': self._secondary_enabled(),
            'lift_secondary_multiplier': self._secondary_multiplier(),
            'grip_channel': self._channel('grip_channel', 2),
            'lift_angle': int(self._current_lift_angle),
            'moving': bool(self._move_thread is not None),
        }

    def up(self) -> bool:
        ok, _ = self.perform_action('start_up')
        return ok

    def down(self) -> bool:
        ok, _ = self.perform_action('start_down')
        return ok

    def hold(self) -> bool:
        ok, _ = self.perform_action('hold')
        return ok

    def release(self) -> bool:
        ok, _ = self.perform_action('release')
        return ok

    def open(self) -> bool:
        return self.release()

    def close(self) -> bool:
        return self.hold()

    def lift(self) -> bool:
        return self.up()

    def raise_up(self) -> bool:
        return self.up()

    def lower(self) -> bool:
        return self.down()
