from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
import sys
from typing import Any


@dataclass(frozen=True)
class DeviceProbe:
    options: list[tuple[str, str]]
    default_value: str
    summary: str
    torch_version: str
    has_cuda: bool
    has_mps: bool


def _fallback_probe(summary: str, *, torch_version: str = 'not available') -> DeviceProbe:
    return DeviceProbe(
        options=[('Auto (best available)', 'auto'), ('CPU', 'cpu')],
        default_value='auto',
        summary=summary,
        torch_version=torch_version,
        has_cuda=False,
        has_mps=False,
    )


def _probe_script() -> str:
    return r'''
import json

try:
    import torch
except Exception as exc:
    print(json.dumps({
        "options": [["Auto (best available)", "auto"], ["CPU", "cpu"]],
        "default_value": "auto",
        "summary": f"PyTorch runtime could not be imported in the isolated probe process: {exc}. Auto will fall back to CPU.",
        "torch_version": "not available",
        "has_cuda": False,
        "has_mps": False,
    }))
    raise SystemExit(0)

torch_version = str(getattr(torch, "__version__", "unknown"))
options = [["Auto (best available)", "auto"]]
summary_parts = [f"Torch {torch_version}"]
has_cuda = False
has_mps = False

cuda = getattr(torch, "cuda", None)
if cuda is not None and callable(getattr(cuda, "is_available", None)) and cuda.is_available():
    has_cuda = True
    try:
        device_count = int(cuda.device_count())
    except Exception:
        device_count = 1
    summary_parts.append(f"CUDA GPUs: {device_count}")
    for index in range(device_count):
        try:
            name = str(cuda.get_device_name(index))
        except Exception:
            name = f"CUDA GPU {index}"
        options.append([f"CUDA:{index} - {name}", f"cuda:{index}"])
else:
    summary_parts.append("CUDA unavailable")

backends = getattr(torch, "backends", None)
mps_backend = getattr(backends, "mps", None) if backends is not None else None
if mps_backend is not None and callable(getattr(mps_backend, "is_available", None)) and mps_backend.is_available():
    has_mps = True
    options.append(["Apple MPS", "mps"])
    summary_parts.append("MPS available")

options.append(["CPU", "cpu"])
default_value = "cuda:0" if has_cuda else ("mps" if has_mps else "auto")
print(json.dumps({
    "options": options,
    "default_value": default_value,
    "summary": " | ".join(summary_parts),
    "torch_version": torch_version,
    "has_cuda": has_cuda,
    "has_mps": has_mps,
}))
'''


def _coerce_probe(payload: Any) -> DeviceProbe:
    if not isinstance(payload, dict):
        return _fallback_probe('Runtime probe returned an invalid payload. Auto will fall back to CPU.')

    raw_options = payload.get('options')
    options: list[tuple[str, str]] = []
    if isinstance(raw_options, list):
        for entry in raw_options:
            if (
                isinstance(entry, (list, tuple))
                and len(entry) == 2
                and isinstance(entry[0], str)
                and isinstance(entry[1], str)
            ):
                options.append((entry[0], entry[1]))
    if not options:
        options = [('Auto (best available)', 'auto'), ('CPU', 'cpu')]

    default_value = payload.get('default_value')
    if not isinstance(default_value, str) or not default_value.strip():
        default_value = 'auto'

    summary = payload.get('summary')
    if not isinstance(summary, str) or not summary.strip():
        summary = 'Runtime probe completed with incomplete details. Auto will fall back to CPU if needed.'

    torch_version = payload.get('torch_version')
    if not isinstance(torch_version, str) or not torch_version.strip():
        torch_version = 'unknown'

    return DeviceProbe(
        options=options,
        default_value=default_value,
        summary=summary,
        torch_version=torch_version,
        has_cuda=bool(payload.get('has_cuda', False)),
        has_mps=bool(payload.get('has_mps', False)),
    )


def probe_runtime() -> DeviceProbe:
    try:
        completed = subprocess.run(
            [sys.executable, '-c', _probe_script()],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _fallback_probe(
            'Runtime probe timed out in an isolated subprocess. Auto will fall back to CPU until the environment is checked.',
        )
    except Exception as exc:
        return _fallback_probe(
            f'Runtime probe could not start in an isolated subprocess: {exc}. Auto will fall back to CPU.',
        )

    stdout = (completed.stdout or '').strip()
    if completed.returncode != 0:
        stderr = (completed.stderr or '').strip()
        detail = stderr.splitlines()[-1] if stderr else f'exit code {completed.returncode}'
        return _fallback_probe(
            'Runtime probe process ended unexpectedly while checking PyTorch/CUDA. '
            f'Auto will fall back to CPU. Details: {detail}',
        )
    if not stdout:
        return _fallback_probe(
            'Runtime probe process returned no data. Auto will fall back to CPU.',
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return _fallback_probe(
            'Runtime probe process returned unreadable data. Auto will fall back to CPU.',
        )
    return _coerce_probe(payload)


def runtime_summary() -> str:
    return probe_runtime().summary


def resolve_device(requested: str | None) -> str:
    probe = probe_runtime()
    raw = (requested or 'auto').strip().lower()
    if not raw or raw == 'auto':
        if probe.has_cuda:
            return '0'
        if probe.has_mps:
            return 'mps'
        return 'cpu'
    if raw == 'cpu':
        return 'cpu'
    if raw in {'gpu', 'cuda'}:
        if probe.has_cuda:
            return '0'
        raise RuntimeError(
            f'GPU was requested but CUDA is unavailable in this Python environment. {probe.summary}. '
            'Install a CUDA-enabled PyTorch build to use an NVIDIA GPU.'
        )
    if raw == 'mps':
        if probe.has_mps:
            return 'mps'
        raise RuntimeError(f'MPS was requested but is unavailable. {probe.summary}.')
    if raw.startswith('cuda:'):
        raw = raw.split(':', 1)[1].strip()
    if all(part.isdigit() for part in raw.split(',') if part):
        if probe.has_cuda:
            return raw
        raise RuntimeError(
            f'CUDA device {raw} was requested but CUDA is unavailable in this Python environment. {probe.summary}. '
            'Install a CUDA-enabled PyTorch build to use an NVIDIA GPU.'
        )
    return raw
