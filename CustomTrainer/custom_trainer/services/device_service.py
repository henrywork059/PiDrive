from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceProbe:
    options: list[tuple[str, str]]
    default_value: str
    summary: str
    torch_version: str
    has_cuda: bool
    has_mps: bool


def probe_runtime() -> DeviceProbe:
    try:
        import torch
    except Exception as exc:
        return DeviceProbe(
            options=[('Auto (best available)', 'auto'), ('CPU', 'cpu')],
            default_value='auto',
            summary=f'PyTorch runtime could not be imported in the UI process: {exc}. Auto will fall back to CPU.',
            torch_version='not available',
            has_cuda=False,
            has_mps=False,
        )

    torch_version = str(getattr(torch, '__version__', 'unknown'))
    options: list[tuple[str, str]] = [('Auto (best available)', 'auto')]
    summary_parts = [f'Torch {torch_version}']
    has_cuda = False
    has_mps = False

    cuda = getattr(torch, 'cuda', None)
    if cuda is not None and callable(getattr(cuda, 'is_available', None)) and cuda.is_available():
        has_cuda = True
        device_count = int(cuda.device_count())
        summary_parts.append(f'CUDA GPUs: {device_count}')
        for index in range(device_count):
            try:
                name = str(cuda.get_device_name(index))
            except Exception:
                name = f'CUDA GPU {index}'
            options.append((f'CUDA:{index} - {name}', f'cuda:{index}'))
    else:
        summary_parts.append('CUDA unavailable')

    backends = getattr(torch, 'backends', None)
    mps_backend = getattr(backends, 'mps', None) if backends is not None else None
    if mps_backend is not None and callable(getattr(mps_backend, 'is_available', None)) and mps_backend.is_available():
        has_mps = True
        options.append(('Apple MPS', 'mps'))
        summary_parts.append('MPS available')

    options.append(('CPU', 'cpu'))
    default_value = 'cuda:0' if has_cuda else ('mps' if has_mps else 'auto')
    return DeviceProbe(
        options=options,
        default_value=default_value,
        summary=' | '.join(summary_parts),
        torch_version=torch_version,
        has_cuda=has_cuda,
        has_mps=has_mps,
    )


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
