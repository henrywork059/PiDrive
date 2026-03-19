from __future__ import annotations

import argparse

from custom_drive.web_app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CustomDrive web monitor.")
    parser.add_argument("--mode", choices=("sim", "live"), default=None, help="Runtime mode. Defaults to CUSTOMDRIVE_MODE or sim.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5050)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    app = create_app(mode=args.mode)
    app.run(host=args.host, port=args.port, threaded=True)
