from __future__ import annotations

import argparse
import socket
import sys
from typing import List

from custom_drive.manual_control_config import load_manual_control_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive GUI control web app.')
    parser.add_argument('--host', default=None, help='Web host override. Defaults to CustomDrive/config/manual_control.json.')
    parser.add_argument('--port', type=int, default=None, help='Web port override. Defaults to CustomDrive/config/manual_control.json.')
    return parser


def _best_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 80))
        return str(sock.getsockname()[0])
    except Exception:
        return '127.0.0.1'
    finally:
        sock.close()


def _candidate_urls(host: str, port: int) -> List[str]:
    host = str(host or '0.0.0.0')
    urls: list[str] = []
    if host in {'0.0.0.0', '::'}:
        urls.append(f'http://127.0.0.1:{port}')
        ip_addr = _best_local_ip()
        if ip_addr not in {'127.0.0.1', '0.0.0.0'}:
            urls.append(f'http://{ip_addr}:{port}')
    else:
        urls.append(f'http://{host}:{port}')
    deduped: list[str] = []
    for item in urls:
        if item not in deduped:
            deduped.append(item)
    return deduped


def main() -> None:
    args = build_parser().parse_args()
    gui_settings = load_manual_control_config()
    server_cfg = gui_settings.get('server', {}) if isinstance(gui_settings, dict) else {}
    host = args.host or str(server_cfg.get('host', '0.0.0.0') or '0.0.0.0')
    port = int(args.port if args.port is not None else server_cfg.get('port', 5050))

    print('=== CustomDrive GUI control launcher ===', flush=True)
    print('Loading PiServer-style GUI control app...', flush=True)
    print('Config file: CustomDrive/config/manual_control.json', flush=True)

    try:
        from custom_drive.gui_control_app import create_app
    except Exception as exc:
        print('Failed to start CustomDrive GUI control.', flush=True)
        print(f'Reason: {exc}', flush=True)
        print('Install the GUI dependency first: python -m pip install -r requirements.txt', flush=True)
        sys.exit(1)

    app = create_app()
    print('GUI control app created successfully.', flush=True)
    print('Open the browser at:', flush=True)
    for url in _candidate_urls(host, port):
        print(f'  {url}', flush=True)
    print('This page uses PiServer CameraService, MotorService, and ControlService directly.', flush=True)
    app.run(host=host, port=port, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
