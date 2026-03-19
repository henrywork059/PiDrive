from __future__ import annotations

import argparse
import sys

from custom_drive.run_settings import load_run_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run the CustomDrive GUI monitor.')
    parser.add_argument('--mode', choices=('sim', 'live'), default=None, help='Runtime backend. Defaults to config/run_settings.json.')
    parser.add_argument('--host', default=None, help='Web host override. Defaults to 0.0.0.0.')
    parser.add_argument('--port', type=int, default=None, help='Web port override. Defaults to 5050.')
    return parser



def main() -> None:
    args = build_parser().parse_args()
    run_settings = load_run_settings()
    host = args.host or '0.0.0.0'
    port = int(args.port if args.port is not None else 5050)
    mode = args.mode or str(run_settings.get('runtime_mode', 'sim'))

    try:
        from custom_drive.web_app import create_app
    except Exception as exc:
        print('Failed to start CustomDrive GUI.')
        print(f'Reason: {exc}')
        print('Install the GUI dependency first: python -m pip install -r requirements.txt')
        sys.exit(1)

    app = create_app(mode=mode)
    app.run(host=host, port=port, threaded=True)


if __name__ == '__main__':
    main()
