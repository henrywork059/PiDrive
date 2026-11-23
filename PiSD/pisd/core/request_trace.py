"""R47: bounded, privacy-safe tracing of failed Flask API mutations.

Only changes failed API JSON responses. Successful responses, HTTP statuses,
motor/servo/AI execution, auth gates, and user configuration are untouched.
Correlation IDs are server generated, never accepted from client headers.
"""
from __future__ import annotations

import re
import secrets
from typing import Any

_MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_SECRET_KEYS = re.compile(r"password|passwd|passphrase|secret|token|authorization|cookie|api[_-]?key|credential", re.I)
_PATH_KEYS = re.compile(r"(?:^|_)(?:path|directory|dirname|filename|file_path)(?:$|_)", re.I)
_SECRET_VALUES = re.compile(
    r"(?:\b(?:password|passwd|passphrase|secret|token|authorization|api[_-]?key)\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|\S+)",
    re.I,
)
_BEARER = re.compile(r"\bBearer\s+\S+", re.I)
_ABSOLUTE_PATHS = re.compile(
    r"(?<![\w])(?:[A-Za-z]:[\\/]|/(?:home|Users|mnt|etc|root|var|tmp|opt|media|run)/)[^\s,;\"'()<>{}]*",
    re.I,
)
_URLS = re.compile(r"https?://\S+", re.I)
_SAFE_OP = re.compile(r"[^a-zA-Z0-9_.-]")
_SAFE_CODE = re.compile(r"^[A-Z0-9_-]{1,48}$")


def safe_diagnostic_text(value: Any, *, limit: int = 240) -> str:
    """Scrub sensitive substrings; limit exported diagnostic length."""
    result = str(value or "")
    result = _URLS.sub("[redacted URL]", result)
    result = _SECRET_VALUES.sub("[redacted credential]", result)
    result = _BEARER.sub("Bearer [redacted]", result)
    result = _ABSOLUTE_PATHS.sub("[redacted path]", result)
    result = re.sub(r"[\r\n\t]+", " ", result)
    return result[:limit]


def safe_diagnostic(value: Any, *, depth: int = 0) -> Any:
    """Sanitize a bounded diagnostic object; not the normal service state."""
    if depth >= 3:
        return "[omitted]"
    if isinstance(value, dict):
        cleaned = {}
        for key, item in list(value.items())[:24]:
            label = str(key)[:48]
            if _SECRET_KEYS.search(label) or _PATH_KEYS.search(label):
                cleaned[label] = "[redacted]"
            else:
                cleaned[label] = safe_diagnostic(item, depth=depth + 1)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [safe_diagnostic(item, depth=depth + 1) for item in value[:12]]
    if isinstance(value, str):
        return safe_diagnostic_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return "[omitted]"


def _operation_name(endpoint: Any) -> str:
    # Flask endpoint is defined by server code, unlike user-controlled URL/query.
    return _SAFE_OP.sub("_", str(endpoint or "unknown"))[:64]


def install_mutation_trace(app) -> None:
    """One concise log line and JSON/header correlation ID for each failed mutation."""
    from flask import jsonify, request

    @app.after_request
    def trace_failed_api_mutation(response):
        if request.method not in _MUTATION_METHODS or not request.path.startswith("/api/"):
            return response

        payload = response.get_json(silent=True) if response.is_json else None
        failed = response.status_code >= 400 or (
            isinstance(payload, dict)
            and (payload.get("ok") is False or payload.get("saved") is False)
        )
        if not failed:
            return response

        correlation_id = secrets.token_hex(8)
        operation = _operation_name(request.endpoint)
        if not isinstance(payload, dict):
            # Unexpected Flask/HTML failures: do not export traceback or path.
            payload = {"ok": False, "message": "Pi request failed. Check the Pi, then retry."}
        else:
            payload = dict(payload)
            for field in ("message", "error"):
                if field in payload:
                    if isinstance(payload[field], str):
                        payload[field] = safe_diagnostic_text(payload[field])
                    elif field == "error":
                        payload[field] = safe_diagnostic(payload[field])

        payload["correlation_id"] = correlation_id
        payload["operation"] = operation
        # Preserve HTTP codes (including historical ok:false/HTTP 200).
        response.set_data(app.json.dumps(payload))
        response.mimetype = "application/json"
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["Cache-Control"] = "no-store"

        code = payload.get("code")
        code = code if isinstance(code, str) and _SAFE_CODE.fullmatch(code) else "-"
        # Never log request bodies, auth headers, passwords, routes, file paths,
        # nested runtime configs, exception reprs, or arbitrary response text.
        app.logger.warning(
            "api_mutation_failure id=%s operation=%s http_status=%d code=%s",
            correlation_id, operation, response.status_code, code,
        )
        return response
