from __future__ import annotations

import argparse
import socket
import sys
from typing import List

from custom_drive.run_settings import load_run_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive GUI monitor.')
    parser.add_argument('--mode', choices=('sim', 'live'), default=None, help='Runtime backend. Defaults to config/run_settings.json.')
    parser.add_argument('--host', default=None, help='Web host override. Defaults to 0.0.0.0.')
    parser.add_argument('--port', type=int, default=None, help='Web port override. Defaults to 5050.')
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
    run_settings = load_run_settings()
    host = args.host or '0.0.0.0'
    port = int(args.port if args.port is not None else 5050)
    mode = args.mode or str(run_settings.get('runtime_mode', 'sim'))

    print('=== CustomDrive GUI launcher ===', flush=True)
    print(f'Launch mode: GUI | runtime backend request: {mode}', flush=True)
    print(f'Run settings file: CustomDrive/config/run_settings.json', flush=True)
    print('Loading web app...', flush=True)

    try:
        from custom_drive.web_app import create_app
    except Exception as exc:
        print('Failed to start CustomDrive GUI.', flush=True)
        print(f'Reason: {exc}', flush=True)
        print('Install the GUI dependency first: python -m pip install -r requirements.txt', flush=True)
        sys.exit(1)

    app = create_app(mode=mode)
    print('Web app created successfully.', flush=True)
    print('Open the browser at:', flush=True)
    for url in _candidate_urls(host, port):
        print(f'  {url}', flush=True)
    print('The mission will only move the real motors when live mode is selected and you press Start Auto.', flush=True)
    print('CustomDrive live mode reuses PiServer CameraService and MotorService.', flush=True)
    app.run(host=host, port=port, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
