#!/usr/bin/env python3
"""
PiSD placeholder main code.

Purpose:
    A clean development sandbox for rebuilding and testing PiServer-style GUI
    and runtime functions from square one without changing the existing
    PiServer component.

Run:
    python PiSD.py

Notes:
    - This file intentionally avoids direct Raspberry Pi hardware imports.
    - The first scaffold provides a tiny Flask status page if Flask is installed.
    - Hardware, camera, motor, model, recorder, and settings layers should be
      added later as separate modules instead of being hardcoded here.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
VERSION = "0.0.0-placeholder"


@dataclass(frozen=True)
class PiSDStatus:
    """Simple status object used by the placeholder API."""

    app: str = "PiSD"
    version: str = VERSION
    mode: str = "placeholder"
    hardware_enabled: bool = False
    camera_enabled: bool = False
    motor_enabled: bool = False
    model_enabled: bool = False
    message: str = "PiSD sandbox is ready for staged GUI and function development."

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        return data


def build_status() -> PiSDStatus:
    """Return current placeholder status.

    Later development can replace this with a real runtime status service.
    """

    return PiSDStatus()


def create_app():
    """Create the optional Flask development app.

    Flask is imported inside this function so the file can still show a useful
    setup message when dependencies have not been installed yet.
    """

    try:
        from flask import Flask, jsonify, render_template_string
    except ImportError as exc:  # pragma: no cover - only used before install
        raise RuntimeError(
            "Flask is not installed. Run: python -m pip install -r requirement.txt"
        ) from exc

    app = Flask(__name__)

    @app.get("/")
    def index():
        status = build_status().to_dict()
        return render_template_string(
            """
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>PiSD Sandbox</title>
                <style>
                    body { font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }
                    main { max-width: 880px; margin: auto; }
                    code, pre { background: #f3f4f6; border-radius: 8px; padding: 0.2rem 0.35rem; }
                    pre { padding: 1rem; overflow-x: auto; }
                    .card { border: 1px solid #ddd; border-radius: 14px; padding: 1rem; }
                </style>
            </head>
            <body>
                <main>
                    <h1>PiSD Sandbox</h1>
                    <p>
                        Clean placeholder workspace for rebuilding and testing
                        PiServer GUI and runtime functions from square one.
                    </p>
                    <div class="card">
                        <h2>Status</h2>
                        <pre>{{ status_json }}</pre>
                    </div>
                    <h2>Next development targets</h2>
                    <ol>
                        <li>Define the new GUI layout and panel structure.</li>
                        <li>Add simulated camera, motor, and status services.</li>
                        <li>Add API endpoints before connecting real Pi hardware.</li>
                        <li>Add repeatable smoke tests for each feature.</li>
                    </ol>
                    <p>API status endpoint: <code>/api/status</code></p>
                </main>
            </body>
            </html>
            """,
            status_json=json.dumps(status, indent=2),
        )

    @app.get("/api/status")
    def api_status():
        return jsonify(build_status().to_dict())

    @app.post("/api/action/not-implemented")
    def api_not_implemented():
        return jsonify(
            {
                "ok": False,
                "error": "not_implemented",
                "message": "This endpoint is reserved for future PiSD function testing.",
            }
        ), 501

    return app


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PiSD placeholder sandbox.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Use 0.0.0.0 on Pi LAN.")
    parser.add_argument("--port", type=int, default=5050, help="Port to bind.")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Print placeholder status JSON and exit without starting Flask.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.status_only:
        print(json.dumps(build_status().to_dict(), indent=2))
        return 0

    try:
        app = create_app()
    except RuntimeError as exc:
        print(f"[PiSD] {exc}", file=sys.stderr)
        print("[PiSD] You can still check the placeholder with: python PiSD.py --status-only")
        return 2

    print(f"[PiSD] Starting placeholder web sandbox at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
