"""PiServer LAN access policy and authentication middleware.

Never store the access token in runtime.json, browser localStorage or URL.
The whole server (including MJPEG, recordings and status) is protected in
LAN mode, not just the motor-control endpoints.
"""
from __future__ import annotations

import hmac
import ipaddress
import os
import secrets
from typing import Mapping


MIN_TOKEN_LENGTH = 32


def configured_access_token(environment: Mapping[str, str] | None = None) -> str:
    environment = os.environ if environment is None else environment
    token = str(environment.get("PISERVER_ACCESS_TOKEN", "") or "").strip()
    if token and len(token) < MIN_TOKEN_LENGTH:
        raise RuntimeError("PISERVER_ACCESS_TOKEN must contain at least 32 characters.")
    return token


def is_loopback_address(address: str | None) -> bool:
    try:
        return bool(ipaddress.ip_address(str(address or "")).is_loopback)
    except ValueError:
        return False


def select_bind_host(environment: Mapping[str, str] | None = None) -> str:
    """Bind to localhost unless an explicit long LAN access token is present."""
    environment = os.environ if environment is None else environment
    token = configured_access_token(environment)
    host = str(environment.get("PISERVER_HOST", "") or "").strip()
    if not host:
        return "0.0.0.0" if token else "127.0.0.1"
    if not token and host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("LAN binding requires PISERVER_ACCESS_TOKEN (32+ characters).")
    return host


def valid_bearer_token(authorization: str | None, expected: str) -> bool:
    if not expected or not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return False
    supplied = authorization[len("Bearer "):]
    return len(supplied) <= 4096 and hmac.compare_digest(supplied, expected)


def same_origin(origin_header: str | None, expected_origin: str) -> bool:
    """An explicit Origin must match; CSRF tokens cover clients omitting Origin."""
    return not origin_header or origin_header == expected_origin


def install_access_control(app) -> None:
    """Register centralized request gating, session login, and CSRF handling."""
    from flask import jsonify, redirect, render_template, request, session, url_for

    token = configured_access_token()
    app.config["PISERVER_TOKEN_REQUIRED"] = bool(token)
    app.secret_key = (os.environ.get("PISERVER_SESSION_SECRET") or secrets.token_hex(32))
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("PISERVER_SESSION_SECURE") == "1",
    )

    @app.before_request
    def protect_routes():
        if not token:
            # Also defend if a WSGI runner binds 0.0.0.0 unexpectedly.
            if not is_loopback_address(request.remote_addr):
                return jsonify(ok=False, message="Remote access requires an access token."), 403
            return None

        # Unauthenticated browser login is the only exception to the auth gate.
        if request.endpoint in {"piserver_login", "piserver_auth_login"}:
            if not same_origin(request.headers.get("Origin"), request.host_url.rstrip("/")):
                return jsonify(ok=False, message="Cross-origin request denied."), 403
            return None

        # Explicit API bearer credentials are not ambient browser cookies and
        # therefore do not require CSRF tokens.
        if valid_bearer_token(request.headers.get("Authorization"), token):
            return None

        if session.get("piserver_authorized") is not True:
            if request.path == "/" and request.method == "GET":
                return redirect(url_for("piserver_login"))
            return jsonify(ok=False, message="Authentication required."), 401

        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not same_origin(request.headers.get("Origin"), request.host_url.rstrip("/")):
                return jsonify(ok=False, message="Cross-origin request denied."), 403
            expected = session.get("piserver_csrf", "")
            supplied = request.headers.get("X-PiServer-CSRF", "")
            if not expected or not hmac.compare_digest(str(supplied), str(expected)):
                return jsonify(ok=False, message="Missing or invalid CSRF token."), 403
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api/") or request.path in {"/", "/login", "/video_feed"}:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/login")
    def piserver_login():
        if not token or session.get("piserver_authorized") is True:
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.post("/api/auth/login")
    def piserver_auth_login():
        if not token:
            return jsonify(ok=False, message="Local-only mode does not use a login token."), 400
        data = request.get_json(silent=True)
        supplied = data.get("token") if isinstance(data, dict) else None
        if not isinstance(supplied, str) or len(supplied) > 4096 or not hmac.compare_digest(supplied, token):
            session.clear()
            return jsonify(ok=False, message="Incorrect access token."), 401
        session.clear()
        session["piserver_authorized"] = True
        session["piserver_csrf"] = secrets.token_urlsafe(32)
        return jsonify(ok=True, message="Access granted.")

    @app.get("/api/auth/csrf")
    def piserver_auth_csrf():
        return jsonify(ok=True, token_required=bool(token), csrf_token=session.get("piserver_csrf", "") if token else "")

    @app.post("/api/auth/logout")
    def piserver_auth_logout():
        session.clear()
        return jsonify(ok=True, message="Signed out.")
