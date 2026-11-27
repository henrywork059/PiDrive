#!/usr/bin/env python3
"""Compare trusted PiDrive revisions using real source methods, without hardware.

Run from a Git checkout with NumPy, pandas, Pillow and OpenCV installed:
    python tools/benchmark_performance_update1.py --base <full SHA> --candidate <full SHA>

Only named preprocessing and preview-table functions are executed. This is an
operation-level benchmark, not a runtime, GUI, physical safety or energy test.
Use only revisions whose source you trust. No user datasets/configs are read.
"""
from __future__ import annotations

import argparse
import ast
import cProfile
import io
import json
import math
import platform
import re
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    'pisd': 'PiSD/pisd/services/ai_drive_service.py',
    'piserver': 'PiServer/piserver/services/model_service.py',
    'trainer': 'piTrainer/piTrainer/services/data/preview_service.py',
}


class NoTiming:
    """Isolate preprocessing without introducing new per-frame instrumentation."""
    def start(self):
        return None

    def observe_elapsed(self, *_args):
        pass


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)


def verify_ref(ref):
    if not re.fullmatch('[0-9a-f]{40}', ref) or git('rev-parse', ref + '^{commit}').strip() != ref:
        raise ValueError('Provide a full, trusted commit SHA')
    return ref


def load_functions(ref, key, namespace):
    source = git('show', f'{ref}:{PATHS[key]}')
    parsed = ast.parse(source, filename=PATHS[key])
    if key == 'trainer':
        names = {'PREVIEW_COLUMN_ORDER', 'dataframe_preview_rows'}
        nodes = [node for node in parsed.body if
                 (isinstance(node, ast.FunctionDef) and node.name in names) or
                 (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))]
        if len(nodes) != 2:
            raise RuntimeError('Trainer preview source changed; inspect before benchmarking')
    else:
        class_name = 'AIDriveService' if key == 'pisd' else 'ModelService'
        owner = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == class_name)
        nodes = [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == '_prepare_input']
        if len(nodes) != 1 or nodes[0].decorator_list:
            raise RuntimeError('Preprocessing method contract changed; inspect before benchmarking')
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, PATHS[key], 'exec'), namespace)
    return namespace['dataframe_preview_rows' if key == 'trainer' else '_prepare_input']


def load_class_method(ref, path, class_name, method_name, namespace, optional=False):
    parsed = ast.parse(git('show', f'{ref}:{path}'), filename=path)
    owner = next(n for n in parsed.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    nodes = [n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == method_name]
    if optional and not nodes:
        return None
    if len(nodes) != 1:
        raise RuntimeError(f'Unexpected method contract: {class_name}.{method_name}')
    node = nodes[0]
    # Extract only the actual function body, not module imports or Qt startup.
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[method_name]


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p) - 1)]


def measure_pair(before, after, repeats, iterations):
    for fn in (before, after):
        fn()
    rounds = [[], []]
    for round_no in range(repeats):
        for index in ((0, 1) if round_no % 2 == 0 else (1, 0)):
            fn = (before, after)[index]
            cpu_start, wall_start = time.process_time_ns(), time.perf_counter_ns()
            for _ in range(iterations):
                fn()
            wall_ms = (time.perf_counter_ns() - wall_start) / (iterations * 1e6)
            cpu_ms = (time.process_time_ns() - cpu_start) / (iterations * 1e6)
            rounds[index].append({'cpu_ms_per_operation': cpu_ms, 'wall_ms_per_operation': wall_ms})
    result = {}
    for name, fn, samples in zip(('before', 'after'), (before, after), rounds):
        # Separate heap tracing from timing; NumPy/Qt/native memory may not be
        # accounted for completely, so do not mislabel this value as RSS.
        tracemalloc.start()
        try:
            fn()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        result[name] = {'rounds': samples, 'cpu_median_ms': statistics.median(s['cpu_ms_per_operation'] for s in samples),
                        'wall_median_ms': statistics.median(s['wall_ms_per_operation'] for s in samples),
                        'wall_p95_round_mean_ms': percentile([s['wall_ms_per_operation'] for s in samples], .95),
                        'traced_heap_peak_bytes_single_operation': peak}
    return result


def process_peak_rss():
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {'peak_rss_bytes': int(value if sys.platform == 'darwin' else value * 1024),
                'rss_scope': 'whole benchmark process, both revisions and imports'}
    except ImportError:
        try:
            import psutil
            peak = getattr(psutil.Process().memory_info(), 'peak_wset', None)
            return {'peak_rss_bytes': peak, 'rss_scope': 'whole benchmark process (Windows peak working set)'}
        except ImportError:
            return {'peak_rss_bytes': None, 'rss_scope': 'unavailable'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--rows', type=int, default=10000)
    parser.add_argument('--profile-dir', type=Path, help='Optional separate cProfile files for each revision/case')
    args = parser.parse_args()
    if args.rounds < 5 or args.rows <= 0:
        parser.error('At least five paired rounds and a positive row count are required')
    refs = [verify_ref(args.base), verify_ref(args.candidate)]
    import cv2
    import numpy as np
    import pandas as pd
    import PIL
    from PIL import Image
    rng = np.random.default_rng(17)
    rgb = rng.integers(0, 256, (240, 426, 3), dtype=np.uint8)
    jpeg = io.BytesIO()
    Image.fromarray(rgb).save(jpeg, format='JPEG', quality=80)
    encoded = jpeg.getvalue()
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    original = bgr.copy()
    df = pd.DataFrame({'frame_id': [str(i) for i in range(args.rows)], 'session': ['session_a'] * args.rows,
                       'steering': rng.random(args.rows, dtype=np.float32), 'throttle': rng.random(args.rows, dtype=np.float32),
                       'mode': ['manual'] * args.rows, 'ts': ['2026-01-01T00:00:00Z'] * args.rows,
                       'abs_image': ['/synthetic/frame.jpg'] * args.rows, 'overlay_settings': [{} for _ in range(args.rows)]})
    cases = {}
    for key in PATHS:
        functions = [load_functions(ref, key, {'np': np, 'pd': pd, 'cv2': cv2, 'Any': object}) for ref in refs]
        if key == 'trainer':
            pair = [lambda fn=fn: fn(df) for fn in functions]
            assert pair[0]() == pair[1](), 'Trainer row parity failed'
            cases[key] = (pair, 3)
        else:
            for size in ((160, 120), (426, 240)):
                svc = SimpleNamespace(performance=NoTiming(), _input_size=size, _lock=threading.RLock(), _backend='tflite')
                if key == 'pisd':
                    pair = [lambda fn=fn, svc=svc: fn(svc, encoded) for fn in functions]
                    before, after = pair[0](), pair[1]()
                    assert before[1] == after[1]
                    np.testing.assert_array_equal(before[0], after[0])
                else:
                    pair = [lambda fn=fn, size=size: fn(None, bgr, size) for fn in functions]
                    np.testing.assert_array_equal(pair[0](), pair[1]())
                    np.testing.assert_array_equal(bgr, original)
                cases[f'{key}_{size[0]}x{size[1]}'] = (pair, 100)
    # Measure the interpreter boundary's same-dtype conversion, separately
    # from decode and resize. Check integer output parity and source ownership.
    tensor = rng.random((1, 240, 426, 3), dtype=np.float32)
    tensor_original = tensor.copy()
    tensor_details = {'dtype': np.float32}
    for key, class_name, method in (
        ('pisd', 'AIDriveService', '_coerce_tflite_input'),
        ('piserver', 'ModelService', '_quantize_if_needed'),
    ):
        funcs = [load_class_method(ref, PATHS[key], class_name, method, {'np': np, 'Any': object}) for ref in refs]
        if key == 'pisd':
            pair = [lambda fn=fn: fn(tensor, tensor_details) for fn in funcs]
        else:
            pair = [lambda fn=fn: fn(None, tensor, tensor_details) for fn in funcs]
        np.testing.assert_array_equal(pair[0](), pair[1]())
        np.testing.assert_array_equal(tensor, tensor_original)
        cases[f'{key}_float32_tensor'] = (pair, 1000)

    # Use the production inverse lookup method and actual rebuild implementation
    # on a deterministic permutation, without a Qt dependency. Report lookup
    # and rebuild separately; this is not end-to-end desktop latency.
    row_path = 'piTrainer/piTrainer/panels/data/preview_model.py'
    sources = rng.permutation(args.rows).tolist()
    queries = rng.integers(0, args.rows, size=1000).tolist()
    lookup_pair = []
    lookup_metadata = []
    for ref in refs:
        model = SimpleNamespace(_source_rows=sources.copy())
        lookup = load_class_method(ref, row_path, 'RecordPreviewModel', 'view_row_for_source_row', {})
        rebuild = load_class_method(ref, row_path, 'RecordPreviewModel', '_rebuild_source_lookup', {}, optional=True)
        rebuild_ms = 0.0
        if rebuild:
            start = time.process_time_ns()
            rebuild(model)
            rebuild_ms = (time.process_time_ns() - start) / 1e6
        lookup_pair.append(lambda lookup=lookup, model=model: [lookup(model, i) for i in queries])
        reverse = getattr(model, '_view_rows', [])
        lookup_metadata.append({'rebuild_cpu_ms_single_observation': rebuild_ms,
                                'reverse_index_items': len(reverse),
                                'reverse_index_list_bytes_excluding_integer_objects': sys.getsizeof(reverse) if reverse else 0})
    assert lookup_pair[0]() == lookup_pair[1](), 'Trainer source lookup parity failed'
    cases['trainer_1000_source_lookups'] = (lookup_pair, 3)

    output = {'baseline': refs[0], 'candidate': refs[1], 'platform': platform.platform(),
              'versions': {'python': sys.version.split()[0], 'numpy': np.__version__, 'pandas': pd.__version__,
                           'opencv': cv2.__version__, 'pillow': PIL.__version__}, 'fixture': {'seed': 17, 'source_size': [426, 240], 'jpeg_quality': 80, 'trainer_rows': args.rows},
              'parity': 'all exact comparisons passed', 'cases': {},
              'source_lookup_index': dict(zip(('before', 'after'), lookup_metadata))}
    for name, (pair, iterations) in cases.items():
        output['cases'][name] = measure_pair(*pair, args.rounds, iterations)
        if args.profile_dir:
            args.profile_dir.mkdir(parents=True, exist_ok=True)
            for label, fn in zip(('before', 'after'), pair):
                profiler = cProfile.Profile()
                profiler.runcall(fn)
                profiler.dump_stats(str(args.profile_dir / f'{name}_{label}.prof'))
    output.update(process_peak_rss())
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
