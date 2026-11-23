#!/usr/bin/env python3
"""Inspect or explicitly reconcile a saved PiSD recording session offline.

Examples:
  python3 scripts/recover_recordings.py 2026-11-22/session_name
  python3 scripts/recover_recordings.py 2026-11-22/session_name --repair --confirm-offline
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.services.recording_recovery import inspect_session, recover_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Inspect or safely recover PiSD JSONL recording metadata.')
    parser.add_argument('session', help='Session folder relative to PiSD/recordings or an absolute path under that root.')
    parser.add_argument('--root', type=Path, default=PROJECT_ROOT / 'recordings')
    parser.add_argument('--repair', action='store_true', help='Write supported metadata and refresh manifest with backups.')
    parser.add_argument('--confirm-offline', action='store_true', help='Confirm PiSD and other recorders are stopped.')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    session_arg = Path(args.session)
    session = (session_arg if session_arg.is_absolute() else root / session_arg).resolve()
    if session == root or root not in session.parents:
        parser.error('Session must be a child folder of the given recordings root.')
    try:
        result = recover_session(session, confirm_offline=args.confirm_offline) if args.repair else inspect_session(session)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f'Recording integrity check failed: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result.get('needs_attention') else 0


if __name__ == '__main__':
    raise SystemExit(main())
