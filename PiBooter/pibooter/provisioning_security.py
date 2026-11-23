"""PiBooter hotspot credential and provisioning request protections."""
from __future__ import annotations

import hmac
import ipaddress
import secrets
from urllib.parse import urlparse

PUBLISHED_HOTSPOT_PASSWORD = 'pibooter1234'


def generate_hotspot_password() -> str:
    """Generate a per-device WPA2 credential (URL-safe, 32+ random characters)."""
    return secrets.token_urlsafe(24)


def hotspot_password_safe(value: object) -> bool:
    """Existing custom WPA passwords stay valid; publicly known one is blocked."""
    if not isinstance(value, str) or not (8 <= len(value) <= 63):
        return False
    return value != PUBLISHED_HOTSPOT_PASSWORD


def authorized_setup_client(remote_ip: str, hotspot_ip: str) -> bool:
    """Only a hotspot client or the device itself may change Wi-Fi profiles."""
    try:
        address = ipaddress.ip_address(remote_ip)
        if address.is_loopback:
            return True
        interface = ipaddress.ip_interface(hotspot_ip)
        return address in interface.network and address != interface.ip
    except (ValueError, TypeError):
        return False


def request_token_matches(submitted: str, expected: str) -> bool:
    return (
        isinstance(submitted, str)
        and isinstance(expected, str)
        and len(expected) >= 32
        and len(submitted) <= 256
        and hmac.compare_digest(submitted, expected)
    )


def trusted_post_origin(origin: str | None, host_header: str | None) -> bool:
    """Reject explicitly cross-origin POSTs. Token required when Origin omitted."""
    if not origin:
        return True  # Older phones may omit Origin for same-site form submits.
    if not host_header or any(ch in host_header for ch in ('/', chr(92), '@', '#', '?')):
        return False
    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    return (
        parsed.scheme == 'http'
        and parsed.netloc.lower() == host_header.lower()
        and not parsed.username
        and not parsed.password
        and parsed.path in ('', '/')
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )
