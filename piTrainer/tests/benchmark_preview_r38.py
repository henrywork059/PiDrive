#!/usr/bin/env python3
"""R38 reproducible, non-destructive Data loader / preview benchmark.

Example (from piTrainer/):
    python tests/benchmark_preview_r38.py --counts 250 2500 10000
    python tests/benchmark_preview_r38.py --counts 250 2500 10000 --qt-preview

Each count runs in a fresh interpreter to avoid retaining pandas/Qt state from
other runs. Fixtures are generated under TemporaryDirectory; no user sessions
or configuration files are read/written. 'Peak RSS' covers the subprocess
lifetime (imports and fixture generation included). The load/filtered timings
measure only the named code path; report this distinction when comparing.
Requires pandas and Pillow. --qt-preview additionally requires PySide6.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def rss_metrics() -> dict[str, float | None]:
    """Return OS peak process RSS when available; never label a heap guess RSS."""
    try:
        import resource  # POSIX
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS reports bytes; Linux reports KiB.
        peak = value / (1024 * 1024) if sys.platform == 'darwin' else value / 1024
        return {'peak_rss_mib': round(peak, 2), 'rss_source': 'resource.ru_maxrss'}
    except ImportError:
        try:
            import psutil  # Optional Windows benchmark dependency
            info = psutil.Process().memory_info()
            peak = getattr(info, 'peak_wset', None)
            if peak:
                return {'peak_rss_mib': round(peak / (1024 * 1024), 2), 'rss_source': 'psutil.peak_wset'}
            return {'peak_rss_mib': None, 'rss_source': 'unavailable; psutil RSS is not peak'}
        except ImportError:
            return {'peak_rss_mib': None, 'rss_source': 'unavailable: install psutil'}


def child_run(count: int, qt_preview: bool, navigate: int) -> dict:
    from PIL import Image
    from piTrainer.services.data.record_loader_service import (
        build_filtered_dataframe, load_records_dataframe,
    )

    with tempfile.TemporaryDirectory(prefix='pitrainer_r38_') as temp:
        root = Path(temp)
        session = root / 'session_a'
        frames = session / 'frames'
        frames.mkdir(parents=True)
        image = frames / 'base.jpg'
        Image.new('RGB', (426, 240), (23, 34, 45)).save(image, quality=70)
        with (session / 'labels.jsonl').open('w', encoding='utf-8') as handle:
            for index in range(count):
                name = f'frame_{index:06}.jpg'
                frame_path = frames / name
                try:
                    os.link(image, frame_path)
                except OSError:
                    # Filesystem fallback is deliberately less space-efficient.
                    frame_path.write_bytes(image.read_bytes())
                handle.write(json.dumps({
                    'frame_id': f'f{index:06}',
                    'frame': f'frames/{name}',
                    'ts': f'2026-01-01T00:00:{index % 60:02d}Z',
                    'mode': 'manual',
                    'steering': 0.2,
                    'throttle': 0.4,
                }) + '\n')

        started = time.perf_counter()
        df = load_records_dataframe(root, ['session_a'])
        load_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        filtered = build_filtered_dataframe(df, only_manual=True)
        filter_ms = (time.perf_counter() - started) * 1000
        result = {
            'rows_requested': count,
            'rows_loaded': len(df),
            'rows_filtered': len(filtered),
            'load_ms': round(load_ms, 2),
            'filter_ms': round(filter_ms, 2),
            'qt_preview': qt_preview,
        }
        if qt_preview:
            os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
            from PySide6.QtWidgets import QApplication
            from piTrainer.utils.image_utils import (
                clear_scaled_pixmap_cache, load_scaled_pixmap, scaled_pixmap_cache_stats,
            )
            application = QApplication.instance() or QApplication([])
            clear_scaled_pixmap_cache()
            source_paths = df['abs_image'].tolist()
            started = time.perf_counter()
            for index in range(navigate):
                # Repeat frames as a user would when cycling/navigating.
                pixmap = load_scaled_pixmap(source_paths[index % len(source_paths)], 960, 540, flip_lr=index % 7 == 0)
                if pixmap is None:
                    raise RuntimeError('Generated fixture image failed to decode')
            result['navigation_ms'] = round((time.perf_counter() - started) * 1000, 2)
            result['navigation_count'] = navigate
            result['cache'] = scaled_pixmap_cache_stats()
            # Retain the application until native pixmap measurements are read.
            del application
        result.update(rss_metrics())
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--counts', type=int, nargs='+', default=[250, 2500, 10000])
    parser.add_argument('--qt-preview', action='store_true', help='Use real offscreen Qt scaled image navigation')
    parser.add_argument('--navigation-count', type=int, default=300)
    parser.add_argument('--child-count', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if any(n <= 0 for n in args.counts) or args.navigation_count < 1:
        parser.error('Counts and navigation-count must be positive.')
    if args.child_count is not None:
        print(json.dumps(child_run(args.child_count, args.qt_preview, args.navigation_count)))
        return 0
    observations = []
    for count in args.counts:
        cmd = [sys.executable, str(Path(__file__).resolve()),
               '--child-count', str(count), '--navigation-count', str(args.navigation_count)]
        if args.qt_preview:
            cmd.append('--qt-preview')
        run = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if run.returncode != 0:
            print(f'Benchmark {count} failed: {run.stderr.strip()}', file=sys.stderr)
            return run.returncode
        observations.append(json.loads(run.stdout.strip().splitlines()[-1]))
    print(json.dumps({
        'sizes': observations,
        'fixture': '426x240 linked JPEG files; generated metadata; not real user sessions',
        'timing': 'load and filter only; peak RSS covers process/import/fixture',
        'environment': {'python': sys.version.split()[0], 'platform': sys.platform},
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
