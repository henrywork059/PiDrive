from __future__ import annotations

import argparse
import socket
import sys
from typing import List


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive GUI control web app.')
    parser.add_argument('--host', default='0.0.0.0', help='Web host. Default: 0.0.0.0')
    parser.add_argument('--port', type=int, default=5050, help='Web port. Default: 5050')
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
    urls: list[str] = []
    if host in {'0.0.0.0', '::'}:
        urls.append(f'http://127.0.0.1:{port}')
        lan_ip = _best_local_ip()
        if lan_ip not in {'127.0.0.1', '0.0.0.0'}:
            urls.append(f'http://{lan_ip}:{port}')
    else:
        urls.append(f'http://{host}:{port}')
    result: list[str] = []
    for item in urls:
        if item not in result:
            result.append(item)
    return result


def main() -> None:
    args = build_parser().parse_args()

    print('CustomDrive GUI control starting...', flush=True)
    print(f'Host: {args.host}', flush=True)
    print(f'Port: {args.port}', flush=True)

    try:
        from custom_drive.gui_control_app import create_app
    except Exception as exc:
        print('Failed to load CustomDrive GUI control.', flush=True)
        print(f'Reason: {exc}', flush=True)
        print('Install dependencies with: python -m pip install -r requirements.txt', flush=True)
        sys.exit(1)

    app = create_app()
    print('Open browser:', flush=True)
    for url in _candidate_urls(args.host, args.port):
        print(url, flush=True)
    print('This GUI uses PiServer CameraService and ControlService.', flush=True)
    print('The drag pad sends real manual motor commands on the Pi when GPIO is available.', flush=True)
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
