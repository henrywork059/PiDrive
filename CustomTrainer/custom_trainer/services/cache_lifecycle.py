"""Immutable, uniquely named YOLO dataset generations and explicit cleanup.

Never destroy a generation while preparing another dataset. Consumers run
against a generation-local YAML rather than the mutable dataset.yaml pointer.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import yaml

MANIFEST = 'cache_manifest.json'
LEASE_FILE = '.reader.lock'
GENERATIONS = 'generations'
STAGING = '.building'


def new_cache_generation(dataset_root: Path) -> tuple[Path, Path]:
    base = Path(dataset_root) / '.customtrainer_yolo_cache'
    published = base / GENERATIONS
    building = base / STAGING
    published.mkdir(parents=True, exist_ok=True)
    building.mkdir(parents=True, exist_ok=True)
    name = f'gen_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}_{uuid.uuid4().hex}'
    staged = building / name
    staged.mkdir(exist_ok=False)
    return staged, published / name


def _sum_cache_entries(lines: list[str], staged: Path, target: Path) -> None:
    for value in lines:
        image = Path(value)
        try:
            relative = image.relative_to(target)
        except ValueError as exc:
            raise ValueError(f'Image path outside generation: {value}') from exc
        if not relative.parts or relative.parts[0] != 'images':
            raise ValueError(f'Invalid generated image path: {value}')
        if not (staged / relative).is_file():
            raise ValueError(f'Generated image missing: {relative}')


def publish_cache_generation(staged: Path, target: Path, spec: dict,
                             *, image_count: int, valid_labels: int) -> None:
    """Validate complete staged lists and atomically publish one generation.

    The caller owns stage cleanup on failure. The published directory is never
    overwritten, and no existing generation is pruned here.
    """
    train = (staged / 'train.txt').read_text(encoding='utf-8').splitlines()
    val = (staged / 'val.txt').read_text(encoding='utf-8').splitlines()
    if len(train) + len(val) != image_count or len(set(train + val)) != image_count:
        raise ValueError('Generated train/validation lists contain missing or duplicate images.')
    if set(train).intersection(val):
        raise ValueError('Generated training and validation lists overlap.')
    _sum_cache_entries(train + val, staged, target)
    if spec.get('path') != target.resolve().as_posix():
        raise ValueError('YAML dataset path must reference the final immutable generation.')
    if spec.get('nc') != len(spec.get('names', [])):
        raise ValueError('YAML class count does not match its names.')
    count_labels = sum(1 for p in (staged / 'labels').rglob('*.txt') if p.is_file())
    if count_labels != valid_labels:
        raise ValueError('Generated labels do not match the validated label count.')
    spec_text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    (staged / 'dataset.yaml').write_text(spec_text, encoding='utf-8')
    manifest = {
        'schema': 'customtrainer-cache-v1', 'generation': target.name,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'images': image_count, 'train': len(train), 'val': len(val),
        'labeled_images': valid_labels, 'class_names': list(spec['names']),
        'train_list_sha256': hashlib.sha256((staged / 'train.txt').read_bytes()).hexdigest(),
        'val_list_sha256': hashlib.sha256((staged / 'val.txt').read_bytes()).hexdigest(),
    }
    (staged / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (staged / LEASE_FILE).touch(exist_ok=False)
    if target.exists():
        raise FileExistsError(f'Cache generation already exists: {target}')
    staged.rename(target)


def atomic_write_yaml(path: Path, spec: dict) -> None:
    """Compatibility pointer: publish only after immutable cache is complete."""
    content = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp',
                                         delete=False) as stream:
            staged = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def _generation_from_yaml(yaml_path: Path) -> Path | None:
    """Only recognize cache YAML produced by this version, not arbitrary YAML."""
    try:
        data = yaml.safe_load(Path(yaml_path).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('path'), str):
            return None
        generation = Path(data['path']).resolve()
        if generation.parent.name != GENERATIONS or generation.parent.parent.name != '.customtrainer_yolo_cache':
            return None
        marker = generation / MANIFEST
        if not marker.is_file():
            return None
        meta = json.loads(marker.read_text(encoding='utf-8'))
        if meta.get('schema') != 'customtrainer-cache-v1' or meta.get('generation') != generation.name:
            return None
        return generation
    except (OSError, ValueError, KeyError, yaml.YAMLError):
        return None


@contextlib.contextmanager
def _file_lock(path: Path, *, reader: bool) -> Iterator[bool]:
    """Nonblocking OS lock: POSIX shared readers; Windows exclusive lease."""
    if os.name == 'nt':
        import msvcrt
        with path.open('r+b') as fd:
            fd.seek(0)
            fd.write(b'0')
            fd.flush()
            fd.seek(0)
            try:
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                yield False
                return
            try:
                yield True
            finally:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        with path.open('rb') as fd:
            try:
                fcntl.flock(fd.fileno(), (fcntl.LOCK_SH if reader else fcntl.LOCK_EX) | fcntl.LOCK_NB)
            except OSError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def generation_reader_lease(yaml_path: str | Path | None):
    """Hold an active CLI training/validation generation until process exit."""
    root = _generation_from_yaml(Path(yaml_path)) if yaml_path else None
    if root is None:
        yield  # Custom user YAML is left alone.
        return
    with _file_lock(root / LEASE_FILE, reader=True) as acquired:
        if not acquired:
            raise RuntimeError('Dataset cache generation is being pruned; restart this task.')
        if (root / '.pruning').exists() or not (root / MANIFEST).is_file():
            raise RuntimeError('Dataset cache generation is not available for this job.')
        yield


def list_cache_generations(root: Path) -> list[dict]:
    """Show known and active generations; never touch other cache paths."""
    base = Path(root) / '.customtrainer_yolo_cache' / GENERATIONS
    active = {_generation_from_yaml(Path(root) / name) for name in ('dataset.yaml', 'data.yaml')}
    result = []
    if not base.is_dir():
        return result
    for item in sorted(base.iterdir(), key=lambda p: p.name, reverse=True):
        if item.is_symlink() or not item.is_dir() or not item.name.startswith('gen_'):
            continue
        try:
            meta = json.loads((item / MANIFEST).read_text(encoding='utf-8'))
            if meta.get('schema') != 'customtrainer-cache-v1' or meta.get('generation') != item.name:
                continue
            with _file_lock(item / LEASE_FILE, reader=False) as lockable:
                busy = not lockable
            result.append({'path': item, 'generation': item.name,
                           'current': item.resolve() in active, 'busy': busy or (item / '.pruning').exists(),
                           'created_utc': meta.get('created_utc', ''),
                           'images': meta.get('images', 0)})
        except (OSError, ValueError, KeyError):
            continue
    result.sort(key=lambda entry: (entry['created_utc'], entry['generation']), reverse=True)
    return result


def prune_cache_generations(root: Path, *, confirm_idle: bool = False,
                            minimum_age_hours: float = 24, keep_latest: int = 2) -> list[Path]:
    """Operator-requested safe pruning; never automatic or while lease held."""
    if not confirm_idle:
        raise ValueError('Explicit --confirm-idle is required; check no training/validation jobs are running.')
    if minimum_age_hours < 24 or keep_latest < 2:
        raise ValueError('Cache pruning requires at least 24 hours age and 2 retained generations.')
    generations = list_cache_generations(root)
    now = time.time()
    deleted = []
    for entry in generations[keep_latest:]:
        p = entry['path']
        if entry['current'] or entry['busy'] or now - p.stat().st_mtime < minimum_age_hours * 3600:
            continue
        with _file_lock(p / LEASE_FILE, reader=False) as acquired:
            if not acquired or entry['current']:
                continue
            # Check that the active compatibility pointer has not moved.
            if p.resolve() in {_generation_from_yaml(Path(root) / name) for name in ('dataset.yaml', 'data.yaml')}:
                continue
            if not (p / MANIFEST).is_file():
                continue
            # Mark deletion while exclusive lock is still held. New readers
            # reject this tombstone even after Windows releases the file lock.
            (p / '.pruning').touch(exist_ok=False)
        try:
            shutil.rmtree(p)
        except OSError:
            # Failed deletion remains quarantined rather than serving partial
            # data. Operators can inspect/remove it when all jobs have exited.
            continue
        deleted.append(p)
    return deleted
