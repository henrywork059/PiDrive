from __future__ import annotations

import argparse
import socket
import sys
from typing import Iterable

from custom_drive.manual_control_config import load_manual_control_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive PiServer-style manual control app.')
    parser.add_argument('--host', default=None, help='Web host override. Defaults to CustomDrive/config/manual_control.json.')
    parser.add_argument('--port', type=int, default=None, help='Web port override. Defaults to CustomDrive/config/manual_control.json.')
    return parser


def _candidate_urls(host: str, port: int) -> list[str]:
    urls: list[str] = [f'http://127.0.0.1:{port}']
    try:
        hostname = socket.gethostname()
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = str(sockaddr[0])
            if ip.startswith('127.') or ip == '0.0.0.0':
                continue
            urls.append(f'http://{ip}:{port}')
    except Exception:
        pass
    if host not in {'0.0.0.0', '::'}:
        urls.insert(0, f'http://{host}:{port}')
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def main() -> None:
    args = build_parser().parse_args()
    manual_cfg = load_manual_control_config()
    server_cfg = manual_cfg.get('server', {}) if isinstance(manual_cfg, dict) else {}
    host = args.host or str(server_cfg.get('host', '0.0.0.0') or '0.0.0.0')
    port = int(args.port if args.port is not None else server_cfg.get('port', 5050))

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
    for url in _candidate_urls(host, port):
        print(f'Open browser: {url}')
    app = create_manual_control_app()
    app.run(host=host, port=port, threaded=True)


if __name__ == '__main__':
    main()
