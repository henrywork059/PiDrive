from __future__ import annotations

import argparse
import sys

from custom_drive.manual_control_config import load_manual_control_config



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive PiServer-style manual control app.')
    parser.add_argument('--host', default=None, help='Web host override. Defaults to CustomDrive/config/manual_control.json.')
    parser.add_argument('--port', type=int, default=None, help='Web port override. Defaults to CustomDrive/config/manual_control.json.')
    return parser



def main() -> None:
    args = build_parser().parse_args()
    manual_cfg = load_manual_control_config()
    server_cfg = manual_cfg.get('server', {}) if isinstance(manual_cfg, dict) else {}
    host = args.host or str(server_cfg.get('host', '0.0.0.0') or '0.0.0.0')
    port = int(args.port if args.port is not None else server_cfg.get('port', 5060))

    try:
        from custom_drive.manual_control_app import create_manual_control_app
    except Exception as exc:
        print('Failed to start CustomDrive manual control.')
        print(f'Reason: {exc}')
        print('Install dependencies first: python -m pip install -r requirements.txt')
        sys.exit(1)

    print('CustomDrive manual control starting...')
    print(f'Host: {host}')
    print(f'Port: {port}')
    print(f'Open browser: http://127.0.0.1:{port}')
    app = create_manual_control_app()
    app.run(host=host, port=port, threaded=True)


if __name__ == '__main__':
    main()
