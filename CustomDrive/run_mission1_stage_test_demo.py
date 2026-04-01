from __future__ import annotations

import argparse
import socket
import sys

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive Mission 1 session web app.')
    parser.add_argument('--host', default=None, help='Web host override. Defaults to CustomDrive/config/mission1_session.json.')
    parser.add_argument('--port', type=int, default=None, help='Web port override. Defaults to CustomDrive/config/mission1_session.json.')
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



def _load_host_port_defaults() -> tuple[str, int]:
    import json
    from pathlib import Path

    config_path = Path(__file__).resolve().parent / 'config' / 'mission1_session.json'
    host = '0.0.0.0'
    port = 5050
    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding='utf-8'))
            if isinstance(raw, dict):
                server_cfg = raw.get('server') or {}
                if isinstance(server_cfg, dict):
                    host = str(server_cfg.get('host', host) or host)
                    port = int(server_cfg.get('port', port))
        except Exception:
            pass
    return host, port



def main() -> None:
    args = build_parser().parse_args()
    default_host, default_port = _load_host_port_defaults()
    host = args.host or default_host
    port = int(args.port if args.port is not None else default_port)

    try:
        from custom_drive.mission1_session_app import create_mission1_session_app
        app = create_mission1_session_app()
    except Exception as exc:
        print('Failed to start CustomDrive Mission 1 session web app.')
        print(f'Reason: {exc}')
        print('Install dependencies first: python -m pip install -r requirements.txt')
        sys.exit(1)

    print('CustomDrive Mission 1 session web app starting...')
    print(f'Host: {host}')
    print(f'Port: {port}')
    print('This app runs the typed start route first, then starts camera + AI tracking for class 1.')
    for url in _candidate_urls(host, port):
        print(f'Open browser: {url}')
    app.run(host=host, port=port, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
