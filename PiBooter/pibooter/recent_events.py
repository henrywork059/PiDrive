"""R49 PiBooter: safe fixed-size projection of the existing bounded state log.

The internal RuntimeState retains its original messages for local debugging.
This public browser view never exports those messages, SSIDs, network
passwords, host/client addresses, subprocess stderr or filesystem paths.
Classification uses only recognized operator/phase phrases.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

_LIMIT = 80
_CATEGORIES = {
    "wifi_connect": ("network", "Wi-Fi connection"),
    "wifi_scan": ("network", "Wi-Fi scan"),
    "wifi_forget": ("network", "Saved Wi-Fi profile removal"),
    "hotspot_start": ("network", "Setup hotspot start"),
    "hotspot_stop": ("network", "Setup hotspot stop"),
    "startup": ("runtime", "PiBooter startup"),
    "setup_session": ("runtime", "Setup session change"),
    "setup_timeout": ("runtime", "Setup window timed out"),
    "network_error": ("network", "NetworkManager error"),
}


def classify(message: Any) -> tuple[str, str] | None:
    """Never return the raw text or its parsed SSID, IP, filename or argument."""
    if not isinstance(message, str):
        return None
    value = message.casefold().strip()
    if "failed to forget saved network" in value or "failed to forget saved wi-fi" in value:
        return ("wifi_forget", "failed")
    if "forgot saved wi-fi profile" in value or "forgot saved network" in value:
        return ("wifi_forget", "succeeded")
    if "wi-fi connection failed" in value or "could not connect to" in value:
        return ("wifi_connect", "failed")
    if "pi connected to" in value or "wi-fi connected successfully" in value:
        return ("wifi_connect", "succeeded")
    if "wi-fi connection attempt" in value or "connection request" in value:
        return ("wifi_connect", "observed")
    if "wi-fi scan refreshed" in value or "loaded " in value and "nearby wi-fi" in value:
        return ("wifi_scan", "succeeded")
    if "failed to start hotspot" in value:
        return ("hotspot_start", "failed")
    if "hotspot started" in value:
        return ("hotspot_start", "succeeded")
    if "failed to stop hotspot" in value:
        return ("hotspot_stop", "failed")
    if "hotspot stopped" in value:
        return ("hotspot_stop", "succeeded")
    if "pibooter controller initialised" in value:
        return ("startup", "observed")
    if "startup hold cancelled" in value:
        return ("setup_session", "succeeded")
    if "no client or web request arrived" in value:
        return ("setup_timeout", "observed")
    if "background monitor error" in value:
        return ("network_error", "failed")
    return None


def project_recent_events(logs: Any, limit: int = _LIMIT) -> list[dict[str, str]]:
    """Bounded sanitization for public GET; no network calls, writes or timers."""
    if not isinstance(logs, list):
        return []
    count = max(1, min(_LIMIT, int(limit)))
    output: list[dict[str, str]] = []
    # Existing logs are already internally bounded. Scan the newest 200 only.
    for entry in logs[-200:]:
        if not isinstance(entry, dict):
            continue
        classified = classify(entry.get("message"))
        if classified is None:
            continue
        op, outcome = classified
        raw_ts = entry.get("ts")
        try:
            stamp = float(raw_ts)
            if not math.isfinite(stamp):
                continue
            at = datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds")
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        category, title = _CATEGORIES[op]
        output.append({
            "timestamp_utc": at,
            "operation": op,
            "category": category,
            "title": title,
            "outcome": outcome,
        })
    return output[-count:]
