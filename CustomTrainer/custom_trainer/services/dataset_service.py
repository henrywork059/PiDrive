from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml


_DATASET_FILENAMES = ('dataset.yaml', 'data.yaml')


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


def build_dataset_spec(class_names: Iterable[str]) -> dict:
    clean_names = [str(name).strip() for name in class_names if str(name).strip()]
    if not clean_names:
        clean_names = ['object']
    return {
        'train': 'images',
        'val': 'images',
        'names': clean_names,
    }


def write_dataset_yaml(path: Path, class_names: Iterable[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    spec = build_dataset_spec(class_names)
    text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding='utf-8')
    return path


def ensure_dataset_yaml(root: Path | None, class_names: Iterable[str], overwrite: bool = False) -> tuple[Path | None, bool]:
    if root is None:
        return None, False
    existing = find_dataset_yaml(root)
    if existing is not None and not overwrite:
        return existing, False
    path = existing or default_dataset_yaml_path(root)
    write_dataset_yaml(path, class_names)
    return path, True
