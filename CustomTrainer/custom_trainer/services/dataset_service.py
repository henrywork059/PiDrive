from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from custom_trainer.services.session_service import discover_sessions


_DATASET_FILENAMES = ('dataset.yaml', 'data.yaml')
_TRAIN_LIST_NAME = 'train.txt'
_VAL_LIST_NAME = 'val.txt'


def find_dataset_yaml(root: Path | None) -> Path | None:
    if root is None:
        return None
    for name in _DATASET_FILENAMES:
        path = root / name
        if path.exists() and path.is_file():
            return path
    return None


def default_dataset_yaml_path(root: Path) -> Path:
    return root / 'dataset.yaml'


def _normalize_class_names(class_names: Iterable[str]) -> list[str]:
    clean_names = [str(name).strip() for name in class_names if str(name).strip()]
    return clean_names or ['object']


def _split_image_paths(image_paths: list[Path]) -> tuple[list[Path], list[Path]]:
    ordered = sorted(image_paths, key=lambda item: item.as_posix().lower())
    if not ordered:
        return [], []
    if len(ordered) == 1:
        return ordered[:], ordered[:]
    val_count = max(1, round(len(ordered) * 0.1))
    if val_count >= len(ordered):
        val_count = 1
    stride = max(1, len(ordered) // val_count)
    val_indices = set(range(stride - 1, len(ordered), stride))
    val_paths = [path for idx, path in enumerate(ordered) if idx in val_indices]
    if not val_paths:
        val_paths = [ordered[-1]]
    train_paths = [path for idx, path in enumerate(ordered) if idx not in val_indices]
    if not train_paths:
        train_paths = ordered[:-1] or ordered[:]
    return train_paths, val_paths


def _write_image_list(path: Path, image_paths: list[Path]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = ''.join(f'{image_path.resolve().as_posix()}\n' for image_path in image_paths)
    previous = path.read_text(encoding='utf-8') if path.exists() else None
    if previous == text:
        return False
    path.write_text(text, encoding='utf-8')
    return True


def build_dataset_spec(root: Path, class_names: Iterable[str]) -> tuple[dict, list[Path], list[Path]]:
    sessions = discover_sessions(root)
    image_paths = [image_path for session in sessions for image_path in session.image_paths]
    train_paths, val_paths = _split_image_paths(image_paths)
    if not train_paths and image_paths:
        train_paths = image_paths[:]
    if not val_paths:
        val_paths = train_paths[:] or image_paths[:]
    spec = {
        'train': (root / _TRAIN_LIST_NAME).resolve().as_posix(),
        'val': (root / _VAL_LIST_NAME).resolve().as_posix(),
        'names': _normalize_class_names(class_names),
    }
    return spec, train_paths, val_paths


def write_dataset_yaml(path: Path, class_names: Iterable[str]) -> tuple[Path, bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    spec, train_paths, val_paths = build_dataset_spec(path.parent, class_names)
    _write_image_list(path.parent / _TRAIN_LIST_NAME, train_paths)
    _write_image_list(path.parent / _VAL_LIST_NAME, val_paths)
    text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    previous = path.read_text(encoding='utf-8') if path.exists() else None
    if previous != text:
        path.write_text(text, encoding='utf-8')
    return path, created


def ensure_dataset_yaml(root: Path | None, class_names: Iterable[str], overwrite: bool = False) -> tuple[Path | None, bool]:
    if root is None:
        return None, False
    existing = find_dataset_yaml(root)
    preferred = default_dataset_yaml_path(root)
    path = existing or preferred
    if existing is not None and existing != preferred and not overwrite:
        return existing, False
    return write_dataset_yaml(path, class_names)
