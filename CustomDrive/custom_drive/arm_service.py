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
    - Press-and-hold gripper motion on servo channel 2 only.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = {}
        self._kit = None
        self._move_thread: threading.Thread | None = None
        self._move_stop = threading.Event()
        self._move_lock = threading.RLock()
        self._move_direction = 0
        self._grip_thread: threading.Thread | None = None
        self._grip_stop = threading.Event()
        self._grip_lock = threading.RLock()
        self._grip_direction = 0
        self._current_lift_angle = 0
        self._current_grip_angle = 0
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
        self.stop_grip_motion()
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
        self._current_grip_angle = self._angle('grip_default_angle', 90)

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
            self.last_message = f'PCA9685 ready on 0x{address:02X}.'
        except Exception as exc:  # pragma: no cover - hardware/env dependent
            self._kit = None
            self.available = False
            self.last_error = str(exc)
            self.last_message = f'Arm init failed: {exc}'
        return self.status()

    def shutdown(self) -> None:
        self.stop_motion()
        self.stop_grip_motion()
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

    def _grip_channel(self) -> int:
        # The gripper must stay on servo channel 2 only, even if older config
        # files still contain a different value.
        return 2

    def _grip_step_angle(self) -> int:
        value = self._config.get('grip_step_angle', 1)
        try:
            value = int(value)
        except Exception:
            value = 1
        return max(1, min(20, value))

    def _grip_rate_deg_per_s(self) -> float:
        value = self._config.get('grip_rate_deg_per_s', 10.0)
        try:
            value = float(value)
        except Exception:
            value = 5.0
        return max(0.5, min(60.0, value))

    def _grip_step_interval_s(self) -> float:
        return max(0.02, min(1.0, self._grip_step_angle() / self._grip_rate_deg_per_s()))

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

    def _apply_grip_angle(self, angle: int) -> None:
        self._set_servo_angle(self._grip_channel(), angle)

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

    def _grip_move_loop(self) -> None:
        while not self._grip_stop.is_set():
            with self._grip_lock:
                direction = self._grip_direction
            if direction == 0:
                break
            step = self._grip_step_angle() * direction
            next_angle = int(max(0, min(180, self._current_grip_angle + step)))
            try:
                self._apply_grip_angle(next_angle)
                self._current_grip_angle = next_angle
                self.last_action = 'open' if direction < 0 else 'close'
                self.last_action_at = time.time()
                self.last_error = ''
                self.last_message = f'Gripper moving {self.last_action}: ch2 -> {self._current_grip_angle}°.'
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Gripper move failed: {exc}'
                break
            self._grip_stop.wait(self._grip_step_interval_s())
        with self._grip_lock:
            self._grip_direction = 0
            self._grip_thread = None
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
        self.last_action = 'idle'
        self.last_action_at = time.time()
        self.last_message = f'Lift stopped at {self._current_lift_angle}°.'
        return True, self.last_message

    def start_grip_motion(self, action: str) -> tuple[bool, str]:
        action_key = str(action or '').strip().lower()
        if action_key not in {'open', 'close'}:
            return False, f'Unsupported gripper motion: {action}'
        if not self.enabled:
            self.last_message = 'Arm disabled in config.'
            return False, self.last_message
        if not self.available:
            self.last_message = self.last_error or 'Arm backend is not available.'
            return False, self.last_message
        direction = -1 if action_key == 'open' else 1
        self.stop_grip_motion()
        with self._grip_lock:
            self._grip_direction = direction
            self._grip_stop = threading.Event()
            self._grip_thread = threading.Thread(target=self._grip_move_loop, name='customdrive-grip-move', daemon=True)
            self._grip_thread.start()
        self.last_action = action_key
        self.last_action_at = time.time()
        self.last_error = ''
        self.last_message = f'Gripper {action_key} started on channel 2.'
        return True, self.last_message

    def stop_grip_motion(self) -> tuple[bool, str]:
        thread = None
        with self._grip_lock:
            thread = self._grip_thread
            self._grip_direction = 0
            self._grip_stop.set()
        if thread and thread.is_alive():
            thread.join(timeout=0.2)
        with self._grip_lock:
            self._grip_thread = None
        self.last_action = 'idle'
        self.last_action_at = time.time()
        self.last_message = f'Gripper stopped at {self._current_grip_angle}° on channel 2.'
        return True, self.last_message

    def perform_action(self, action: str) -> tuple[bool, str]:
        action_key = str(action or '').strip().lower()
        action_key = {
            'unclamp': 'start_open',
            'grab': 'start_close',
            'clamp': 'start_close',
            'lift': 'start_up',
            'raise_': 'start_up',
            'raise_up': 'start_up',
            'lower': 'start_down',
        }.get(action_key, action_key)

        if action_key in {'start_up', 'start-down', 'start_down'}:
            return self.start_motion('up' if action_key == 'start_up' else 'down')
        if action_key in {'start_open', 'start_close'}:
            return self.start_grip_motion('open' if action_key == 'start_open' else 'close')
        if action_key == 'stop':
            self.stop_grip_motion()
            return self.stop_motion()
        if action_key == 'stop_lift':
            return self.stop_motion()
        if action_key == 'stop_grip':
            return self.stop_grip_motion()
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
            'hold': ('grip_channel', 'grip_hold_angle', 2, 70),
            'release': ('grip_channel', 'grip_release_angle', 2, 130),
            'open': ('grip_channel', 'grip_release_angle', 2, 130),
            'close': ('grip_channel', 'grip_hold_angle', 2, 70),
        }
        if action_key not in mapping:
            message = f'Unknown arm action: {action}'
            self.last_error = message
            self.last_message = message
            return False, message

        channel_key, angle_key, default_channel, default_angle = mapping[action_key]
        channel = self._grip_channel() if 'grip' in channel_key else self._channel(channel_key, default_channel)
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
            'grip_channel': self._grip_channel(),
            'lift_angle': int(self._current_lift_angle),
            'grip_angle': int(self._current_grip_angle),
            'moving': bool(self._move_thread is not None),
            'grip_moving': bool(self._grip_thread is not None),
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
