"""R34: read-only, credential-free guidance for the short PiBooter setup window.

This projection does not activate a setup session, refresh a deadline, scan Wi-Fi,
run nmcli, or change a network. Existing NetworkManager and shutdown rules own
the connection.
"""
from __future__ import annotations

from typing import Any

STATES = frozenset({"scanning", "connecting", "connected", "failed", "window_closing", "ready", "starting"})


def project_onboarding(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    info = snapshot if isinstance(snapshot, dict) else {}
    attempt = info.get("connection_attempt") if isinstance(info.get("connection_attempt"), dict) else {}
    hotspot = info.get("hotspot") if isinstance(info.get("hotspot"), dict) else {}
    last_status = info.get("last_status") if isinstance(info.get("last_status"), dict) else {}
    phase = str(info.get("phase") or "").strip().lower()
    attempt_status = str(attempt.get("status") or "").strip().lower()
    session_active = info.get("session_active") is True
    shutdown = info.get("should_exit") is True
    remaining = info.get("startup_remaining_s")
    try:
        remaining_s = max(0, int(remaining)) if remaining is not None else None
    except (TypeError, ValueError, OverflowError):
        remaining_s = None

    # Keep this order intentional: confirmed attempt state wins over a
    # NetworkManager 'hotspot' phase during handover or restoration.
    if attempt_status == "success":
        state = "connected"
    elif attempt_status == "running":
        state = "connecting"
    elif attempt_status == "error":
        state = "failed"
    elif phase == "error":
        state = "failed"
    elif phase == "connected":
        state = "connected"
    elif shutdown and not session_active:
        state = "window_closing"
    elif not session_active and remaining_s is not None and remaining_s <= 2:
        state = "window_closing"
    elif info.get("scan_in_progress") is True:
        state = "scanning"
    elif phase == "hotspot" or hotspot.get("active") is True:
        state = "ready"
    else:
        state = "starting"

    if state == "connecting":
        headline = "Connecting to Wi-Fi"
        summary = "The Pi is attempting to join the selected Wi-Fi network."
        guidance = "Do not submit again while connecting. The setup hotspot may disconnect briefly during Wi-Fi handover."
    elif state == "connected":
        headline = "Connected to Wi-Fi"
        summary = "The Pi has joined a non-hotspot network."
        if last_status.get("last_known_ip"):
            guidance = "Reconnect your phone to the same router Wi-Fi, then try the last known Pi IP below. PiBooter will exit after setup."
        else:
            guidance = "Reconnect your phone to the same router Wi-Fi. Use the Pi hostname or check the router for its current IP. PiBooter will exit after setup."
    elif state == "failed":
        headline = "Wi-Fi setup failed"
        summary = "The last connection attempt did not succeed." if attempt_status == "error" else "PiBooter cannot finish Wi-Fi setup."
        if attempt_status == "error" and hotspot.get("active") is True:
            guidance = "Reconnect your phone to the PiBooter hotspot if needed. Check the Wi-Fi name and password, then submit again. The password must be entered again."
        elif attempt_status == "error":
            guidance = "The setup hotspot may not have restarted. If it does not reappear, restart PiBooter locally to open a new setup window; check the Wi-Fi name/password before retrying."
        elif "password" in str(info.get("message") or "").lower() and "hotspot" in str(info.get("message") or "").lower():
            guidance = "The setup hotspot is disabled. Provision a private hotspot password locally on the Pi, then restart PiBooter."
        else:
            guidance = "Check NetworkManager and the Wi-Fi adapter on the Pi, then restart PiBooter. No automatic hotspot extension will occur."
    elif state == "window_closing":
        headline = "Setup window closing"
        summary = "No eligible setup client has activated the short first-client window."
        guidance = "PiBooter will stop the hotspot and exit. To retry after it closes, restart PiBooter or reboot the Pi; the window is not extended automatically."
    elif state == "scanning":
        headline = "Scanning nearby Wi-Fi"
        summary = "Looking for visible networks."
        guidance = "Wait for the scan results. If your network is not listed, enter its SSID manually; some adapters cannot rescan while hosting a hotspot."
    elif state == "ready":
        headline = "Ready for Wi-Fi setup"
        summary = "The PiBooter setup hotspot is available."
        guidance = "Choose a scanned Wi-Fi network or enter its SSID manually, then provide its password and connect. The hotspot password is never shown here."
    else:
        headline = "Starting Wi-Fi setup"
        summary = "PiBooter is checking the network and setup hotspot."
        guidance = "Connect your phone to the PiBooter hotspot promptly. Without an eligible client, the startup window ends automatically."

    return {
        "state": state,
        "headline": headline,
        "summary": summary,
        "next_action": guidance,
        "session_active": session_active,
        "startup_remaining_s": remaining_s if not session_active else None,
        "retry_available": state == "failed" and session_active and hotspot.get("active") is True,
        "scan_in_progress": info.get("scan_in_progress") is True,
    }
