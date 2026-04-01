from __future__ import annotations

import threading
import time
from typing import Any


class ArmService:
    """Pi-side arm service for CustomDrive GUI control.

    Current behavior:
    - servo 0 and servo 1 are controlled directly and independently
    - gripper remains on servo 2
    - all moving controls are press-and-hold
    - hold refresh and serialized PCA9685 writes are preserved

    Backward compatibility:
    - legacy grouped lift actions (start_up/start_down/stop_lift) are still accepted
    - they now proxy to both direct servo channels together
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = {}
        self._kit = None
        self._servo_io_lock = threading.RLock()

        self._servo_threads: dict[int, threading.Thread | None] = {0: None, 1: None}
        self._servo_stops: dict[int, threading.Event] = {0: threading.Event(), 1: threading.Event()}
        self._servo_locks: dict[int, threading.RLock] = {0: threading.RLock(), 1: threading.RLock()}
        self._servo_directions: dict[int, int] = {0: 0, 1: 0}
        self._current_servo_angles: dict[int, int] = {0: 90, 1: 90}

        self._grip_thread: threading.Thread | None = None
        self._grip_stop = threading.Event()
        self._grip_lock = threading.RLock()
        self._grip_direction = 0
        self._current_grip_angle = 70

        self._hold_thread: threading.Thread | None = None
        self._hold_stop = threading.Event()
        self._hold_lock = threading.RLock()

        self.last_action = 'idle'
        self.last_error = ''
        self.last_message = 'Arm disabled.'
        self.last_action_at = 0.0
        self.backend = 'disabled'
        self.available = False
        self.enabled = False
        self.reload(config or {})

    def reload(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        self.stop_hold_refresh()
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

        primary_default = self._angle('lift_down_angle', 90)
        secondary_default = self._secondary_default_angle(primary_default)
        self._current_servo_angles[0] = primary_default
        self._current_servo_angles[1] = secondary_default
        self._current_grip_angle = self._angle('grip_hold_angle', 70)

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

            self._apply_servo_angle(0, self._current_servo_angles[0])
            if self._servo_enabled(1):
                self._apply_servo_angle(1, self._current_servo_angles[1])
            self._apply_grip_angle(self._current_grip_angle)
            self.start_hold_refresh()
            if self._servo_enabled(1):
                self.last_message = (
                    f'PCA9685 ready on 0x{address:02X}. '
                    f'Servo 0 hold {self._current_servo_angles[0]}°; '
                    f'servo 1 hold {self._current_servo_angles[1]}°; '
                    f'grip hold {self._current_grip_angle}°.'
                )
            else:
                self.last_message = (
                    f'PCA9685 ready on 0x{address:02X}. '
                    f'Servo 0 hold {self._current_servo_angles[0]}°; '
                    f'grip hold {self._current_grip_angle}°.'
                )
        except Exception as exc:  # pragma: no cover - hardware/env dependent
            self._kit = None
            self.available = False
            self.last_error = str(exc)
            self.last_message = f'Arm init failed: {exc}'
        return self.status()

    def shutdown(self) -> None:
        self.stop_hold_refresh()
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
        value = self._config.get('lift_step_angle', 1)
        try:
            value = int(value)
        except Exception:
            value = 1
        return max(1, min(45, value))

    def _speed_multiplier(self) -> float:
        value = self._config.get('speed_multiplier', 2.0)
        try:
            value = float(value)
        except Exception:
            value = 2.0
        return max(0.25, min(8.0, value))

    def _hold_refresh_enabled(self) -> bool:
        return bool(self._config.get('hold_refresh_enabled', True))

    def _hold_refresh_interval_s(self) -> float:
        value = self._config.get('hold_refresh_interval_s', 0.75)
        try:
            value = float(value)
        except Exception:
            value = 0.75
        return max(0.1, min(10.0, value))

    def _step_interval_s(self) -> float:
        value = self._config.get('lift_step_interval_s', 0.1)
        try:
            value = float(value)
        except Exception:
            value = 0.1
        return max(0.02, min(1.0, value / self._speed_multiplier()))

    def _direction_sign(self, key: str, default: int) -> int:
        value = self._config.get(key, default)
        try:
            value = int(value)
        except Exception:
            value = int(default)
        return -1 if value < 0 else 1

    def _lift_up_direction(self) -> int:
        return self._direction_sign('lift_up_direction', -1)

    def _grip_open_direction(self) -> int:
        return self._direction_sign('grip_open_direction', -1)

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
        return 2

    def _servo_channel(self, index: int) -> int:
        return self._channel('lift_channel', 0) if index == 0 else self._secondary_channel()

    def _servo_enabled(self, index: int) -> bool:
        if index == 0:
            return True
        return bool(self._secondary_enabled())

    def _secondary_default_angle(self, primary_angle: int) -> int:
        if not self._secondary_enabled():
            return self._angle('lift_down_angle', primary_angle)
        return int(round(max(0, min(180, primary_angle * self._secondary_multiplier()))))

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
            value = 10.0
        value *= self._speed_multiplier()
        return max(0.5, min(90.0, value))

    def _grip_step_interval_s(self) -> float:
        return max(0.02, min(1.0, self._grip_step_angle() / self._grip_rate_deg_per_s()))

    def _servo_action_name_for_direction(self, index: int, direction: int) -> str:
        return f'servo{index}_{"positive" if direction > 0 else "negative"}'

    def _grip_action_name_for_direction(self, direction: int) -> str:
        return 'open' if direction == self._grip_open_direction() else 'close'

    def _set_servo_angle(self, channel: int, angle: int) -> None:
        if not self.enabled:
            raise RuntimeError('Arm is disabled in config.')
        if self._kit is None or not self.available:
            if self.last_error:
                raise RuntimeError(self.last_error)
            raise RuntimeError('Arm backend is not available.')
        with self._servo_io_lock:
            self._kit.servo[channel].angle = max(0, min(180, int(angle)))

    def _apply_servo_angle(self, index: int, angle: int) -> None:
        if not self._servo_enabled(index):
            raise RuntimeError(f'Servo {index} is disabled in config.')
        angle = max(0, min(180, int(angle)))
        self._set_servo_angle(self._servo_channel(index), angle)

    def _apply_grip_angle(self, angle: int) -> None:
        self._set_servo_angle(self._grip_channel(), max(0, min(180, int(angle))))

    def _servo_loop(self, index: int) -> None:
        stop_event = self._servo_stops[index]
        lock = self._servo_locks[index]
        while not stop_event.is_set():
            with lock:
                direction = self._servo_directions[index]
            if direction == 0:
                break
            step = self._step_angle() * direction
            next_angle = int(max(0, min(180, self._current_servo_angles[index] + step)))
            if next_angle == self._current_servo_angles[index]:
                self.last_action = self._servo_action_name_for_direction(index, direction)
                self.last_action_at = time.time()
                self.last_error = ''
                self.last_message = f'Servo {index} limit reached at {self._current_servo_angles[index]}°.'
                stop_event.wait(self._step_interval_s())
                continue
            try:
                self._apply_servo_angle(index, next_angle)
                self._current_servo_angles[index] = next_angle
                self.last_action = self._servo_action_name_for_direction(index, direction)
                self.last_action_at = time.time()
                self.last_error = ''
                self.last_message = f'Servo {index} moving {"+" if direction > 0 else "-"}: ch{self._servo_channel(index)} -> {self._current_servo_angles[index]}°.'
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Servo {index} move failed: {exc}'
                break
            stop_event.wait(self._step_interval_s())
        with lock:
            self._servo_directions[index] = 0
            self._servo_threads[index] = None
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
            if next_angle == self._current_grip_angle:
                self.last_action = self._grip_action_name_for_direction(direction)
                self.last_action_at = time.time()
                self.last_error = ''
                self.last_message = f'Gripper limit reached at {self._current_grip_angle}° on channel 2.'
                self._grip_stop.wait(self._grip_step_interval_s())
                continue
            try:
                self._apply_grip_angle(next_angle)
                self._current_grip_angle = next_angle
                self.last_action = self._grip_action_name_for_direction(direction)
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

    def _is_any_direct_servo_moving(self) -> bool:
        return any(thread is not None and thread.is_alive() for thread in self._servo_threads.values())

    def _hold_refresh_loop(self) -> None:
        while not self._hold_stop.wait(self._hold_refresh_interval_s()):
            if not self.enabled or not self.available:
                continue
            if not self._hold_refresh_enabled():
                continue
            if self._is_any_direct_servo_moving():
                continue
            with self._grip_lock:
                grip_busy = self._grip_thread is not None or self._grip_direction != 0
            if grip_busy:
                continue
            try:
                self._apply_servo_angle(0, self._current_servo_angles[0])
                if self._servo_enabled(1):
                    self._apply_servo_angle(1, self._current_servo_angles[1])
                self._apply_grip_angle(self._current_grip_angle)
                if self.last_error:
                    self.last_error = ''
                    if self._servo_enabled(1):
                        self.last_message = (
                            f'Arm hold restored: servo 0 {self._current_servo_angles[0]}°; '
                            f'servo 1 {self._current_servo_angles[1]}°; '
                            f'grip {self._current_grip_angle}°.'
                        )
                    else:
                        self.last_message = (
                            f'Arm hold restored: servo 0 {self._current_servo_angles[0]}°; '
                            f'grip {self._current_grip_angle}°.'
                        )
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Arm hold refresh failed: {exc}'

    def start_hold_refresh(self) -> tuple[bool, str]:
        if not self.enabled:
            self.last_message = 'Arm disabled in config.'
            return False, self.last_message
        if not self.available:
            self.last_message = self.last_error or 'Arm backend is not available.'
            return False, self.last_message
        if not self._hold_refresh_enabled():
            self.last_message = 'Arm hold refresh disabled in config.'
            return False, self.last_message
        with self._hold_lock:
            if self._hold_thread is not None and self._hold_thread.is_alive():
                return True, 'Arm hold refresh already running.'
            self._hold_stop = threading.Event()
            self._hold_thread = threading.Thread(target=self._hold_refresh_loop, name='customdrive-arm-hold', daemon=True)
            self._hold_thread.start()
        return True, 'Arm hold refresh started.'

    def stop_hold_refresh(self) -> tuple[bool, str]:
        thread = None
        with self._hold_lock:
            thread = self._hold_thread
            self._hold_stop.set()
        if thread and thread.is_alive():
            thread.join(timeout=0.3)
        with self._hold_lock:
            self._hold_thread = None
        return True, 'Arm hold refresh stopped.'

    def start_servo_motion(self, index: int, direction: int) -> tuple[bool, str]:
        if index not in {0, 1}:
            return False, f'Unsupported servo index: {index}'
        if not self.enabled:
            self.last_message = 'Arm disabled in config.'
            return False, self.last_message
        if not self.available:
            self.last_message = self.last_error or 'Arm backend is not available.'
            return False, self.last_message
        if not self._servo_enabled(index):
            self.last_message = f'Servo {index} is disabled in config.'
            return False, self.last_message
        self.stop_servo_motion(index)
        with self._servo_locks[index]:
            self._servo_directions[index] = 1 if direction >= 0 else -1
            self._servo_stops[index] = threading.Event()
            self._servo_threads[index] = threading.Thread(target=self._servo_loop, args=(index,), name=f'customdrive-servo{index}-move', daemon=True)
            self._servo_threads[index].start()
        self.last_action = self._servo_action_name_for_direction(index, self._servo_directions[index])
        self.last_action_at = time.time()
        self.last_error = ''
        self.last_message = f'Servo {index} {"+" if self._servo_directions[index] > 0 else "-"} started.'
        return True, self.last_message

    def stop_servo_motion(self, index: int) -> tuple[bool, str]:
        if index not in {0, 1}:
            return False, f'Unsupported servo index: {index}'
        thread = None
        with self._servo_locks[index]:
            thread = self._servo_threads[index]
            self._servo_directions[index] = 0
            self._servo_stops[index].set()
        if thread and thread.is_alive():
            thread.join(timeout=0.2)
        with self._servo_locks[index]:
            self._servo_threads[index] = None
        if self.enabled and self.available and self._servo_enabled(index):
            try:
                self._apply_servo_angle(index, self._current_servo_angles[index])
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Servo {index} hold failed: {exc}'
                return False, self.last_message
        self.last_action = 'idle'
        self.last_action_at = time.time()
        self.last_error = ''
        self.last_message = f'Servo {index} stopped and held at {self._current_servo_angles[index]}°.'
        return True, self.last_message

    def start_motion(self, action: str) -> tuple[bool, str]:
        action_key = str(action or '').strip().lower()
        if action_key not in {'up', 'down'}:
            return False, f'Unsupported lift motion: {action}'
        direction = self._lift_up_direction() if action_key == 'up' else -self._lift_up_direction()
        results = [self.start_servo_motion(0, direction)]
        if self._servo_enabled(1):
            results.append(self.start_servo_motion(1, direction))
        ok = all(item[0] for item in results)
        if ok:
            self.last_action = action_key
            self.last_action_at = time.time()
            self.last_error = ''
            self.last_message = f'Legacy lift {action_key} started on servo 0 and servo 1.' if self._servo_enabled(1) else f'Legacy lift {action_key} started on servo 0.'
            return True, self.last_message
        message = '; '.join(item[1] for item in results if item[1])
        self.last_error = message
        self.last_message = message
        return False, message

    def stop_motion(self) -> tuple[bool, str]:
        results = [self.stop_servo_motion(0)]
        if self._servo_enabled(1):
            results.append(self.stop_servo_motion(1))
        ok = all(item[0] for item in results)
        if ok:
            self.last_action = 'idle'
            self.last_action_at = time.time()
            self.last_error = ''
            self.last_message = (
                f'Servo 0 held at {self._current_servo_angles[0]}° and servo 1 held at {self._current_servo_angles[1]}°.'
                if self._servo_enabled(1)
                else f'Servo 0 held at {self._current_servo_angles[0]}°.'
            )
            return True, self.last_message
        message = '; '.join(item[1] for item in results if item[1])
        self.last_error = message
        self.last_message = message
        return False, message

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
        open_direction = self._grip_open_direction()
        direction = open_direction if action_key == 'open' else -open_direction
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
        if self.enabled and self.available:
            try:
                self._apply_grip_angle(self._current_grip_angle)
            except Exception as exc:
                self.last_error = str(exc)
                self.last_message = f'Gripper hold failed: {exc}'
                return False, self.last_message
        self.last_action = 'idle'
        self.last_action_at = time.time()
        self.last_error = ''
        self.last_message = f'Gripper stopped and held at {self._current_grip_angle}° on channel 2.'
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
            'start_servo0_plus': 'start_servo0_positive',
            'start_servo1_plus': 'start_servo1_positive',
            'start_servo0_minus': 'start_servo0_negative',
            'start_servo1_minus': 'start_servo1_negative',
            'servo0_plus': 'start_servo0_positive',
            'servo1_plus': 'start_servo1_positive',
            'servo0_minus': 'start_servo0_negative',
            'servo1_minus': 'start_servo1_negative',
        }.get(action_key, action_key)

        if action_key in {'start_servo0_positive', 'start_servo0_negative'}:
            return self.start_servo_motion(0, 1 if action_key.endswith('positive') else -1)
        if action_key in {'start_servo1_positive', 'start_servo1_negative'}:
            return self.start_servo_motion(1, 1 if action_key.endswith('positive') else -1)
        if action_key == 'stop_servo0':
            return self.stop_servo_motion(0)
        if action_key == 'stop_servo1':
            return self.stop_servo_motion(1)

        if action_key in {'start_up', 'start_down', 'start-down'}:
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

        mapping = {
            'hold': ('grip_hold_angle', 70),
            'release': ('grip_release_angle', 130),
            'open': ('grip_release_angle', 130),
            'close': ('grip_hold_angle', 70),
        }
        if action_key not in mapping:
            message = f'Unknown arm action: {action}'
            self.last_error = message
            self.last_message = message
            return False, message

        angle_key, default_angle = mapping[action_key]
        channel = self._grip_channel()
        angle = self._angle(angle_key, default_angle)
        try:
            self._set_servo_angle(channel, angle)
            self._current_grip_angle = angle
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
            'servo0_channel': self._servo_channel(0),
            'servo1_channel': self._servo_channel(1),
            'servo1_enabled': self._servo_enabled(1),
            'lift_channel': self._servo_channel(0),
            'lift_channel_secondary': self._servo_channel(1),
            'lift_secondary_enabled': self._servo_enabled(1),
            'lift_secondary_multiplier': self._secondary_multiplier(),
            'grip_channel': self._grip_channel(),
            'speed_multiplier': float(self._speed_multiplier()),
            'lift_up_direction': int(self._lift_up_direction()),
            'grip_open_direction': int(self._grip_open_direction()),
            'servo0_angle': int(self._current_servo_angles[0]),
            'servo1_angle': int(self._current_servo_angles[1]),
            'lift_angle': int(self._current_servo_angles[0]),
            'grip_angle': int(self._current_grip_angle),
            'hold_refresh_enabled': bool(self._hold_refresh_enabled()),
            'hold_refresh_interval_s': float(self._hold_refresh_interval_s()),
            'hold_refresh_running': bool(self._hold_thread is not None and self._hold_thread.is_alive()),
            'moving': self._is_any_direct_servo_moving(),
            'servo0_moving': bool(self._servo_threads[0] is not None and self._servo_threads[0].is_alive()),
            'servo1_moving': bool(self._servo_threads[1] is not None and self._servo_threads[1].is_alive()),
            'grip_moving': bool(self._grip_thread is not None and self._grip_thread.is_alive()),
            'direct_servo_control': True,
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
