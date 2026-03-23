from __future__ import annotations

import time
from typing import Any


class ArmService:
    """Simple Pi-side arm service for CustomDrive manual control.

    This keeps the backend lightweight and debuggable:
    - Uses PCA9685 via ``adafruit_servokit`` when enabled.
    - Exposes simple actions: up / down / hold / release.
    - Provides alias methods so future code can reuse the same object in
      mission logic or bridge-style sequences.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = {}
        self._kit = None
        self.last_action = 'idle'
        self.last_error = ''
        self.last_message = 'Arm disabled.'
        self.last_action_at = 0.0
        self.backend = 'disabled'
        self.available = False
        self.enabled = False
        self.reload(config or {})

    def reload(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        cfg = dict(config or {})
        self._config = cfg
        self._kit = None
        self.last_error = ''
        self.last_message = 'Arm disabled.'
        self.last_action = 'idle'
        self.backend = str(cfg.get('backend', 'pca9685') or 'pca9685').strip().lower()
        self.enabled = bool(cfg.get('enabled', False))
        self.available = False

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

    def _set_servo_angle(self, channel: int, angle: int) -> None:
        if not self.enabled:
            raise RuntimeError('Arm is disabled in config.')
        if self._kit is None or not self.available:
            if self.last_error:
                raise RuntimeError(self.last_error)
            raise RuntimeError('Arm backend is not available.')
        self._kit.servo[channel].angle = angle

    def perform_action(self, action: str) -> tuple[bool, str]:
        action_key = str(action or '').strip().lower()
        action_key = {
            'open': 'release',
            'unclamp': 'release',
            'close': 'hold',
            'grab': 'hold',
            'clamp': 'hold',
            'lift': 'up',
            'raise_': 'up',
            'raise_up': 'up',
            'lower': 'down',
        }.get(action_key, action_key)

        mapping = {
            'up': ('lift_channel', 'lift_up_angle', 0, 40),
            'down': ('lift_channel', 'lift_down_angle', 0, 115),
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
            'grip_channel': self._channel('grip_channel', 1),
        }

    # Alias helpers so the object can be reused by bridge-style code later.
    def up(self) -> bool:
        ok, _ = self.perform_action('up')
        return ok

    def down(self) -> bool:
        ok, _ = self.perform_action('down')
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
