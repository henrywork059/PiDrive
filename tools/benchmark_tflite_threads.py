"""Offline TFLite thread comparison. Never imports or commands motor services."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import random
import statistics
import time
from pathlib import Path

import numpy as np


def resolve_interpreter():
    errors = []
    for name in ('tflite_runtime.interpreter', 'ai_edge_litert.interpreter',
                 'tensorflow.lite.python.interpreter'):
        try:
            return importlib.import_module(name).Interpreter, name
        except (ImportError, AttributeError) as exc:
            errors.append(f'{name}: {exc}')
    raise RuntimeError('; '.join(errors))


def run_trial(factory, model, inputs, threads, warmup, invocations):
    kwargs = {'model_path': str(model)}
    if threads is not None:
        kwargs['num_threads'] = threads
    interpreter = factory(**kwargs)
    interpreter.allocate_tensors()
    info = interpreter.get_input_details()
    outputs = interpreter.get_output_details()
    shape = tuple(int(n) for n in info[0]['shape']) if len(info) == 1 else ()
    if (len(shape) != 4 or shape[0] != 1 or shape[-1] != 3 or min(shape) <= 0
            or inputs.ndim != 4 or inputs.shape[1:] != shape[1:]
            or inputs.dtype != np.dtype(info[0]['dtype'])):
        raise ValueError('Expected matched prepared NHWC RGB input tensors and exact dtype')
    if len(inputs) == 0 or len(outputs) not in (1, 2):
        raise ValueError('Empty input fixture or unsupported output contract')
    sizes = [int(np.prod(x['shape'])) for x in outputs]
    if sizes not in ([2], [1, 1]):
        raise ValueError('Expected two ordered steering/throttle output values')

    def infer(i):
        interpreter.set_tensor(info[0]['index'], inputs[i % len(inputs):i % len(inputs)+1])
        interpreter.invoke()
        result = [np.asarray(interpreter.get_tensor(x['index'])) for x in outputs]
        if any(not np.all(np.isfinite(x)) for x in result):
            raise ValueError('Nonfinite inference output')
        return result

    for i in range(warmup):
        infer(i)
    digest = hashlib.sha256()
    latencies = []
    start_cpu = time.process_time_ns()
    for i in range(invocations):
        start = time.perf_counter_ns()
        result = infer(i)
        latencies.append((time.perf_counter_ns() - start) / 1e6)
        for item in result:
            digest.update(str(item.dtype).encode('ascii'))
            digest.update(str(item.shape).encode('ascii'))
            digest.update(item.tobytes())
    cpu_ms = (time.process_time_ns() - start_cpu) / 1e6 / invocations
    return {'threads': threads, 'cpu_ms_per_inference': cpu_ms,
            'p50_ms': statistics.median(latencies),
            'p95_ms': float(np.percentile(latencies, 95)),
            'output_sha256': digest.hexdigest()}


def compare(factory, model, inputs, thread_counts=(1, 2, 4), rounds=5,
            warmup=10, invocations=100, seed=17):
    if rounds < 1 or warmup < 0 or invocations < 1:
        raise ValueError('Invalid benchmark lengths')
    if not thread_counts or len(set(thread_counts)) != len(thread_counts) or any(
            type(n) is not int or not 1 <= n <= 16 for n in thread_counts):
        raise ValueError('Thread counts must be unique integers in 1..16')
    rng = random.Random(seed)
    trials = []
    for round_no in range(rounds):
        order = [None, *thread_counts]
        rng.shuffle(order)
        row = {'round': round_no + 1, 'order': order, 'results': []}
        for count in order:
            try:
                row['results'].append(run_trial(factory, model, inputs, count, warmup, invocations))
            except Exception as exc:
                if count is None:
                    raise
                row['results'].append({'threads': count, 'error': f'{type(exc).__name__}: {exc}'})
        trials.append(row)
    baseline = [r for row in trials for r in row['results'] if r['threads'] is None]
    reference = baseline[0]['output_sha256']
    summary = []
    for count in [None, *thread_counts]:
        results = [r for row in trials for r in row['results'] if r['threads'] == count]
        valid = [r for r in results if 'error' not in r]
        complete = len(valid) == rounds
        summary.append({'threads': count, 'complete': complete,
                        'exact_output_parity': complete and all(r['output_sha256'] == reference for r in valid),
                        'median_cpu_ms_per_inference': statistics.median(r['cpu_ms_per_inference'] for r in valid) if valid else None,
                        'median_p95_ms': statistics.median(r['p95_ms'] for r in valid) if valid else None})
    return {'rounds': trials, 'summary': summary, 'seed': seed,
            'warmup': warmup, 'invocations': invocations,
            'cpu_includes': 'set_tensor, invoke, get_tensor, output validation and hashing',
            'deployment_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True, help='Prepared N,H,W,3 .npy tensor fixture')
    parser.add_argument('--threads', type=int, nargs='+', default=[1, 2, 4])
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--warmup', type=int, default=10)
    parser.add_argument('--invocations', type=int, default=100)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    factory, backend = resolve_interpreter()
    inputs = np.load(args.inputs, allow_pickle=False)
    report = compare(factory, args.model, inputs, tuple(args.threads), args.rounds,
                     args.warmup, args.invocations, args.seed)
    report.update(backend=backend, model_sha256=hashlib.sha256(args.model.read_bytes()).hexdigest(),
                  inputs_sha256=hashlib.sha256(args.inputs.read_bytes()).hexdigest(),
                  input_shape=list(inputs.shape), input_dtype=str(inputs.dtype))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(x['complete'] and x['exact_output_parity'] for x in report['summary']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
