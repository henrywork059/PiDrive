"""Inspect or explicitly prune inactive CustomTrainer YOLO cache generations.

Run from CustomTrainer/: python manage_dataset_cache.py SESSIONS_ROOT [--prune --confirm-idle]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from custom_trainer.services.cache_lifecycle import list_cache_generations, prune_cache_generations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Inspect CustomTrainer immutable dataset caches.')
    parser.add_argument('root', type=Path, help='Sessions dataset root (not a generated cache directory)')
    parser.add_argument('--prune', action='store_true', help='Prune only old inactive generated cache versions')
    parser.add_argument('--confirm-idle', action='store_true', help='Confirm no external YOLO jobs are reading old caches')
    parser.add_argument('--minimum-age-hours', type=float, default=24)
    parser.add_argument('--keep-latest', type=int, default=2)
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f'Not a directory: {args.root}')
    try:
        if args.prune:
            removed = prune_cache_generations(args.root, confirm_idle=args.confirm_idle,
                minimum_age_hours=args.minimum_age_hours, keep_latest=args.keep_latest)
            print(f'Pruned {len(removed)} inactive cache generation(s).')
            for path in removed:
                print(f'[pruned] {path}')
        for entry in list_cache_generations(args.root):
            tags = ', '.join(tag for tag, yes in [('current',entry['current']),('busy',entry['busy'])] if yes) or 'retained'
            print(f"{entry['generation']}: images={entry['images']}, created={entry['created_utc']}, {tags}")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
