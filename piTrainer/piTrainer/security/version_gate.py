from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "manifest_url": "",
    "timeout_seconds": 4,
    "fail_closed": False,
    "cache_hours": 12,
}


@dataclass(frozen=True)
class VersionGateResult:
    allowed: bool
    title: str = "PiTrainer version access"
    message: str = ""
    detail: str = ""
    source: str = "disabled"


def _component_root() -> Path:
    # .../piTrainer/piTrainer/security/version_gate.py -> .../piTrainer
    return Path(__file__).resolve().parents[2]


def _config_path() -> Path:
    candidates: list[Path] = []

    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        candidates.append(Path(bundled_root) / "config" / "version_gate.json")

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "config" / "version_gate.json")

    candidates.append(_component_root() / "config" / "version_gate.json")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _cache_path() -> Path:
    appdata = os.environ.get("LOCALAPPDATA")
    if appdata:
        base = Path(appdata) / "PiDrive" / "piTrainer"
    else:
        base = Path.home() / ".pitrainer"
    return base / "version_gate_cache.json"


def load_version_gate_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    path = _config_path()
    if not path.exists():
        return config
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return config
    if isinstance(loaded, dict):
        config.update(loaded)
    return config


def _fetch_manifest(url: str, timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "PiTrainer-VersionGate/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read(128 * 1024)
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest is not a JSON object.")
    return manifest


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _save_cache(manifest: dict[str, Any], app_version: str) -> None:
    path = _cache_path()
    payload = {
        "checked_at_utc": _now_utc().isoformat().replace("+00:00", "Z"),
        "app_version": app_version,
        "manifest": manifest,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        # Cache is only a convenience fallback. Access decisions must not crash
        # because a user profile folder is read-only or unavailable.
        pass


def _load_fresh_cache(cache_hours: float, app_version: str) -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists() or cache_hours <= 0:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get("app_version", "")) != app_version:
        return None
    checked_at = _parse_utc(str(payload.get("checked_at_utc", "")))
    if not checked_at:
        return None
    if _now_utc() - checked_at > timedelta(hours=float(cache_hours)):
        return None
    manifest = payload.get("manifest")
    return manifest if isinstance(manifest, dict) else None


def _version_parts(value: str) -> tuple[int, ...] | None:
    parts = [part for part in re.split(r'[^0-9]+', str(value or '')) if part != '']
    if not parts:
        return None
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        return None


def _compare_versions(left: str, right: str) -> int | None:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    if left_parts is None or right_parts is None:
        return None
    width = max(len(left_parts), len(right_parts))
    left_parts = left_parts + (0,) * (width - len(left_parts))
    right_parts = right_parts + (0,) * (width - len(right_parts))
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _message_from_manifest(manifest: dict[str, Any], fallback: str) -> str:
    message = str(manifest.get("message") or fallback).strip()
    support = str(manifest.get("support_message") or "").strip()
    if support:
        message = f"{message}\n\n{support}"
    latest = str(manifest.get("latest") or "").strip()
    if latest:
        message = f"{message}\n\nLatest allowed version: {latest}"
    return message


def _evaluate_manifest(manifest: dict[str, Any], app_version: str, source: str) -> VersionGateResult:
    app_name = str(manifest.get("app") or "").strip()
    if app_name and app_name.lower() != "pitrainer":
        return VersionGateResult(
            allowed=False,
            title="PiTrainer access check failed",
            message="The online access manifest is not for PiTrainer.",
            detail=f"Manifest app field: {app_name}",
            source=source,
        )

    blocked_versions = set(_as_str_list(manifest.get("blocked_versions")))
    allowed_versions = set(_as_str_list(manifest.get("allowed_versions")))
    minimum_version = str(manifest.get("minimum_version") or "").strip()
    minimum_compare = _compare_versions(app_version, minimum_version) if minimum_version else None

    if app_version in blocked_versions:
        return VersionGateResult(
            allowed=False,
            title="PiTrainer version disabled",
            message=_message_from_manifest(
                manifest,
                "This PiTrainer version is no longer enabled. Please update to the latest version.",
            ),
            detail=f"Current version {app_version} is listed in blocked_versions.",
            source=source,
        )

    if minimum_version and minimum_compare is not None and minimum_compare < 0:
        return VersionGateResult(
            allowed=False,
            title="PiTrainer version too old",
            message=_message_from_manifest(
                manifest,
                "This PiTrainer version is older than the minimum enabled version.",
            ),
            detail=f"Current version {app_version} is older than minimum_version {minimum_version}.",
            source=source,
        )

    # If the manifest provides minimum_version, treat v9+ patch builds as valid
    # even when the older allowed_versions list still contains only the stable
    # baseline. This keeps future 0.9.x bug-fix patches from being blocked while
    # still blocking lower versions.
    minimum_allows_current = bool(minimum_version and minimum_compare is not None and minimum_compare >= 0)
    if allowed_versions and app_version not in allowed_versions and not minimum_allows_current:
        return VersionGateResult(
            allowed=False,
            title="PiTrainer version not allowed",
            message=_message_from_manifest(
                manifest,
                "This PiTrainer version is not in the allowed version list.",
            ),
            detail=f"Current version {app_version} is not listed in allowed_versions.",
            source=source,
        )

    return VersionGateResult(
        allowed=True,
        title="PiTrainer version allowed",
        message=f"PiTrainer {app_version} is allowed by the online manifest.",
        source=source,
    )


def check_version_gate(app_version: str) -> VersionGateResult:
    config = load_version_gate_config()
    if not bool(config.get("enabled", False)):
        return VersionGateResult(allowed=True, source="disabled")

    url = str(config.get("manifest_url") or "").strip()
    if not url:
        if bool(config.get("fail_closed", False)):
            return VersionGateResult(
                allowed=False,
                title="PiTrainer access check is not configured",
                message="The version gate is enabled, but no manifest URL is configured.",
                source="config",
            )
        return VersionGateResult(
            allowed=True,
            message="Version gate is enabled but no manifest URL is configured; opening because fail_closed is false.",
            source="config",
        )

    timeout_seconds = max(1.0, float(config.get("timeout_seconds", 4) or 4))
    cache_hours = max(0.0, float(config.get("cache_hours", 0) or 0))
    fail_closed = bool(config.get("fail_closed", False))

    try:
        manifest = _fetch_manifest(url, timeout_seconds)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        cached_manifest = _load_fresh_cache(cache_hours, app_version)
        if cached_manifest:
            cached_result = _evaluate_manifest(cached_manifest, app_version, source="cache")
            if cached_result.allowed:
                return VersionGateResult(
                    allowed=True,
                    title="PiTrainer version allowed from cache",
                    message="The online version check could not be reached, but a recent valid check is cached.",
                    detail=str(exc),
                    source="cache",
                )
            return cached_result
        if fail_closed:
            return VersionGateResult(
                allowed=False,
                title="PiTrainer access check failed",
                message=(
                    "PiTrainer could not verify this version online, so it will not open.\n\n"
                    "Please check the internet connection and try again."
                ),
                detail=str(exc),
                source="network",
            )
        return VersionGateResult(
            allowed=True,
            title="PiTrainer access check unavailable",
            message="PiTrainer could not verify this version online, but fail_closed is false, so it will open.",
            detail=str(exc),
            source="network",
        )

    result = _evaluate_manifest(manifest, app_version, source="online")
    if result.allowed:
        _save_cache(manifest, app_version)
    return result
