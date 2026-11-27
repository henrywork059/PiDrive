"""PiSD LAN authorization. Secrets stay outside saved runtime settings."""
from __future__ import annotations

import hmac
import ipaddress
import os
import secrets
from urllib.parse import urlsplit
from typing import Mapping

from pisd.core.errors import PiSDErrorCodes

MIN_TOKEN_LENGTH = 32


def configured_access_token(environment: Mapping[str, str] | None = None) -> str:
    env = os.environ if environment is None else environment
    token = str(env.get("PISD_ACCESS_TOKEN", "") or "")
    if token and (len(token) < MIN_TOKEN_LENGTH or len(token) > 4096 or
                  not token.isascii() or any(not 33 <= ord(ch) <= 126 for ch in token)):
        raise RuntimeError("PISD_ACCESS_TOKEN must be 32–4096 printable ASCII characters without spaces.")
    return token


def is_loopback(address: str | None) -> bool:
    try:
        return ipaddress.ip_address(str(address or "")).is_loopback
    except ValueError:
        return False


def validate_bind_host(host: str, environment: Mapping[str, str] | None = None) -> None:
    token = configured_access_token(environment)
    if not token and not (host == "localhost" or is_loopback(host)):
        raise RuntimeError("LAN binding requires PISD_ACCESS_TOKEN (32+ characters).")


def _matches(supplied, expected: str) -> bool:
    return (isinstance(supplied, str) and len(supplied) <= 4096 and
            hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")))


def _same_origin(request, *, require_proof: bool) -> bool:
    """Reject explicit cross-origin requests and require browser provenance for cookies.

    Modern same-origin fetch, native forms and sendBeacon provide Origin and/or
    Sec-Fetch-Site. This avoids adding an async CSRF-token dependency to STOP.
    Never trust X-Forwarded-* headers to establish the origin.
    """
    origin = request.headers.get("Origin")
    site = request.headers.get("Sec-Fetch-Site")
    if origin is not None and origin != request.host_url.rstrip("/"):
        return False
    if site is not None and site != "same-origin":
        return False
    return not require_proof or origin is not None or site == "same-origin"


def install_access_control(app, token: str, *, emulator_frame_port: int | None = None) -> None:
    if emulator_frame_port is not None and (type(emulator_frame_port) is not int or not 1024 <= emulator_frame_port <= 65535):
        raise ValueError("Invalid emulator control port.")
    from flask import jsonify, redirect, render_template, request, session, url_for

    app.secret_key = secrets.token_bytes(32)
    app.config.update(
        PISD_TOKEN_REQUIRED=bool(token),
        SESSION_COOKIE_NAME="pisd_operator_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("PISD_SESSION_SECURE") == "1",
    )

    def denied(message, status=403):
        return jsonify(ok=False, code=PiSDErrorCodes.API_AUTH_REQUIRED if status == 401
                       else PiSDErrorCodes.API_ACCESS_DENIED, message=message), status

    @app.before_request
    def protect_routes():
        mutation = request.method not in {"GET", "HEAD", "OPTIONS"}
        if not token:
            try:
                host = urlsplit(request.host_url).hostname
            except ValueError:
                host = None
            # Also reject DNS-rebinding hostnames even when peer is loopback.
            if not is_loopback(request.remote_addr) or not (host == "localhost" or is_loopback(host)):
                return denied("Remote access requires an operator token.")
            if mutation and not _same_origin(request, require_proof=False):
                return denied("Cross-origin request denied.")
            # Legacy local scripts can omit browser headers; reject simple HTML
            # form bodies without provenance (possible old-browser CSRF).
            if mutation and request.mimetype in {"application/x-www-form-urlencoded", "multipart/form-data", "text/plain"} and not _same_origin(request, require_proof=True):
                return denied("Browser request origin could not be verified.")
            return None

        if request.endpoint in {"pisd_login", "pisd_login_submit"}:
            if mutation and not _same_origin(request, require_proof=True):
                return denied("Login origin could not be verified.")
            return None

        # Explicit bearer credentials are not ambient browser cookies.
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer ") and _matches(authorization[7:], token):
            if mutation and not _same_origin(request, require_proof=False):
                return denied("Cross-origin request denied.")
            return None

        if session.get("pisd_authorized") is not True:
            if request.method == "GET" and not request.path.startswith(("/api/", "/testing/static/")) and request.path != "/video_feed":
                return redirect(url_for("pisd_login"))
            return denied("Operator authentication required.", 401)

        if mutation and not _same_origin(request, require_proof=True):
            return denied("Browser request origin could not be verified.")
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if (emulator_frame_port is not None and app.config.get("pisd_runtime_mode") == "emulator"
                and is_loopback(request.remote_addr) and request.host == request.host_url.split("//", 1)[-1].rstrip("/")
                and request.host.split(":", 1)[0] == "127.0.0.1"):
            # CSP checks all ancestors; trust only the selected controller origin.
            response.headers.pop("X-Frame-Options", None)
            response.headers.add("Content-Security-Policy", f"frame-ancestors http://127.0.0.1:{emulator_frame_port}")
        else:
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if not request.path.startswith("/testing/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/login")
    def pisd_login():
        if not token or session.get("pisd_authorized") is True:
            return redirect("/")
        return render_template("login.html", error="")

    @app.post("/login")
    def pisd_login_submit():
        if not token:
            return redirect("/")
        # No token in URL, cookie, request trace, or settings.
        if not _matches(request.form.get("token"), token):
            session.clear()
            return render_template("login.html", error="Incorrect operator token."), 401
        session.clear()
        session["pisd_authorized"] = True
        return redirect("/", code=303)
