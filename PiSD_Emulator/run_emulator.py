#!/usr/bin/env python3
"""Launch the local PiSD Emulator control workspace."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = Path(__file__).resolve().parent
if str(COMPONENT_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPONENT_ROOT))

from pisd_emulator.control_app import create_control_app  # noqa: E402
from pisd_emulator.runtime import PiSDRuntime  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PiSD local hardware and driving emulator.")
    parser.add_argument("--control-port", type=int, default=8760, help="Local browser workspace port (default: 8760).")
    parser.add_argument("--pisd-port", type=int, default=5050, help="Local PiSD server port (default: 5050).")
    parser.add_argument("--workspace", type=Path, default=None, help="Isolated emulator config, model, and recording directory.")
    parser.add_argument("--open-browser", action="store_true", help="Open the emulator control workspace in the default browser.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not 1024 <= args.control_port <= 65535:
        print("Control port must be between 1024 and 65535.", file=sys.stderr)
        return 2
    runtime = PiSDRuntime(PROJECT_ROOT, workspace=args.workspace, port=args.pisd_port, control_port=args.control_port)
    app = create_control_app(runtime)
    try:
        from werkzeug.serving import make_server

        server = make_server("127.0.0.1", args.control_port, app, threaded=True)
    except OSError as exc:
        print(f"Could not bind emulator control server on 127.0.0.1:{args.control_port}: {exc}", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{args.control_port}/"
    print(f"PiSD Emulator control workspace: {url}")
    print("Physical GPIO and motor access are disabled in emulator mode.")
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping PiSD Emulator...")
    finally:
        runtime.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
