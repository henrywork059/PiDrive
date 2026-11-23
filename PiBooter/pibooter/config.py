from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from .provisioning_security import PUBLISHED_HOTSPOT_PASSWORD, generate_hotspot_password


DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 80,
        "log_limit": 200,
        "monitor_interval_s": 5,
        "poll_interval_s": 1,
        "startup_wait_s": 5,
        "connection_wait_s": 45,
        "scan_cache_ttl_s": 30,
        "shutdown_after_success_s": 1,
    },
    "network": {
        "wifi_interface": "wlan0",
        "ethernet_interface": "eth0",
        "hotspot_connection_name": "PiBooter Hotspot",
        "hotspot_ssid_prefix": "PiBooter",
        "hotspot_password": "pibooter1234",
        "hotspot_ip": "192.168.4.1/24",
        "hotspot_url": "http://192.168.4.1/",
        "hotspot_band": "bg",
        "hotspot_channel": 6,
        "hotspot_autostart_when_unconfigured": True,
        "known_wifi_priority": 50,
        "country": "",
        "allow_open_wifi": True,
    },
    "runtime": {
        "last_status_path": "runtime/last_status.json",
    },
    "ui": {
        "title": "PiBooter Wi-Fi Setup",
        "subtitle": "Connect your Raspberry Pi to home Wi-Fi from a phone or tablet.",
        "status_refresh_s": 3,
        "show_known_connections": True,
    },
}


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {key: deepcopy(value) for key, value in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(override)


def _sanitize_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value_int))


class ConfigStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.load_error = ""
        self.recovery_backup: Path | None = None
        self.data = self.load()

    def _write_atomic(self, data: dict[str, Any]) -> None:
        """Replace only a complete serialized file; protect credentials on new files."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                stream.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _backup_invalid(self) -> None:
        """Never rename or delete the user's original invalid config."""
        try:
            raw = self.path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()[:16]
            backup = self.path.with_name(f"{self.path.name}.corrupt-{digest}")
            if backup.exists():
                if backup.read_bytes() != raw:
                    raise OSError("existing recovery copy does not match the source")
            else:
                shutil.copy2(self.path, backup)
            self.recovery_backup = backup
        except OSError as exc:
            self.load_error += f" Backup could not be created: {exc}"

    def load(self) -> dict[str, Any]:
        self.load_error = ""
        self.recovery_backup = None
        data = deepcopy(DEFAULT_CONFIG)
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(loaded, dict):
                    raise ValueError("The root must be a JSON object")
                for section in ("server", "network", "runtime", "ui"):
                    if section in loaded and not isinstance(loaded[section], dict):
                        raise ValueError(f"'{section}' must be a JSON object")
                data = _deep_merge(data, loaded)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                # Defaults are usable for diagnostics but NEVER overwrite the bad file.
                self.load_error = f"Settings could not be loaded: {exc}. Original preserved."
                self._backup_invalid()
                return self._normalize(data)
            data = self._normalize(data)
            if data != loaded:
                self._write_atomic(data)
            return data

        data = self._normalize(data)
        # A genuinely new config receives a unique secret. Existing configs,
        # including the checked-in legacy template, are never silently rotated.
        data['network']['hotspot_password'] = generate_hotspot_password()
        self._write_atomic(data)
        return data

    def save(self, *, replace_invalid: bool = False) -> None:
        if self.load_error and self.path.exists() and not replace_invalid:
            raise RuntimeError("Invalid settings are preserved; restore or repair the original before saving, or explicitly use replace_invalid=True.")
        self._write_atomic(self.data)
        self.load_error = ""

    def provision_hotspot_password(self, *, rotate: bool = False) -> bool:
        """Explicitly rotate the published example, or any credential on request.

        Does not rewrite invalid settings or existing custom credentials unless
        the operator specifically requests rotation. Preserves all other keys.
        """
        if self.load_error:
            raise RuntimeError('Repair the invalid settings file before provisioning a hotspot password.')
        current = self.data['network']['hotspot_password']
        if not rotate and current != PUBLISHED_HOTSPOT_PASSWORD:
            return False
        previous = self.data
        revised = deepcopy(previous)
        revised['network']['hotspot_password'] = generate_hotspot_password()
        try:
            self.data = revised
            self.save()
        except BaseException:
            self.data = previous
            raise
        return True

    def reload(self) -> dict[str, Any]:
        self.data = self.load()
        return self.data

    def runtime_status_path(self) -> Path:
        raw = str(self.data.get("runtime", {}).get("last_status_path") or "runtime/last_status.json")
        path = Path(raw)
        if path.is_absolute():
            return path
        return (self.path.parent.parent / path).resolve()

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        server = data.setdefault("server", {})
        network = data.setdefault("network", {})
        runtime = data.setdefault("runtime", {})
        ui = data.setdefault("ui", {})

        server["host"] = str(server.get("host") or "0.0.0.0")
        server["port"] = _sanitize_int(server.get("port"), 80, 1, 65535)
        server["log_limit"] = _sanitize_int(server.get("log_limit"), 200, 20, 2000)
        server["monitor_interval_s"] = _sanitize_int(server.get("monitor_interval_s"), 5, 1, 300)
        server["poll_interval_s"] = _sanitize_int(server.get("poll_interval_s"), 1, 1, 10)
        server["startup_wait_s"] = _sanitize_int(server.get("startup_wait_s"), 5, 1, 120)
        server["connection_wait_s"] = _sanitize_int(server.get("connection_wait_s"), 45, 5, 180)
        server["scan_cache_ttl_s"] = _sanitize_int(server.get("scan_cache_ttl_s"), 30, 5, 600)
        server["shutdown_after_success_s"] = _sanitize_int(server.get("shutdown_after_success_s"), 1, 0, 30)

        network["wifi_interface"] = str(network.get("wifi_interface") or "wlan0")
        network["ethernet_interface"] = str(network.get("ethernet_interface") or "eth0")
        network["hotspot_connection_name"] = str(network.get("hotspot_connection_name") or "PiBooter Hotspot")
        network["hotspot_ssid_prefix"] = str(network.get("hotspot_ssid_prefix") or "PiBooter")
        network["hotspot_password"] = self._normalize_hotspot_password(network.get("hotspot_password"))
        network["hotspot_ip"] = str(network.get("hotspot_ip") or "192.168.4.1/24")
        network["hotspot_url"] = str(network.get("hotspot_url") or "http://192.168.4.1/")
        network["hotspot_band"] = str(network.get("hotspot_band") or "bg")
        network["hotspot_channel"] = _sanitize_int(network.get("hotspot_channel"), 6, 1, 165)
        network["hotspot_autostart_when_unconfigured"] = bool(network.get("hotspot_autostart_when_unconfigured", True))
        network["known_wifi_priority"] = _sanitize_int(network.get("known_wifi_priority"), 50, -999, 999)
        network["country"] = str(network.get("country") or "").strip().upper()
        network["allow_open_wifi"] = bool(network.get("allow_open_wifi", True))

        runtime["last_status_path"] = str(runtime.get("last_status_path") or "runtime/last_status.json")

        ui["title"] = str(ui.get("title") or "PiBooter Wi-Fi Setup")
        ui["subtitle"] = str(ui.get("subtitle") or "Connect your Raspberry Pi to home Wi-Fi from a phone or tablet.")
        ui["status_refresh_s"] = _sanitize_int(ui.get("status_refresh_s"), 3, 0, 60)
        ui["show_known_connections"] = bool(ui.get("show_known_connections", True))

        return data

    @staticmethod
    def _normalize_hotspot_password(value: Any) -> str:
        password = str(value or "pibooter1234")
        # Do not pad a short operator password with a public, predictable
        # suffix. Retain it for diagnosis and block hotspot activation until
        # the operator explicitly rotates the credential.
        return password[:63]

    def compute_hotspot_ssid(self) -> str:
        prefix = self.data["network"]["hotspot_ssid_prefix"].strip() or "PiBooter"
        hostname = socket.gethostname().strip() or "pi"
        suffix = hostname[-6:].replace(" ", "")
        return f"{prefix}-{suffix}" if suffix else prefix
