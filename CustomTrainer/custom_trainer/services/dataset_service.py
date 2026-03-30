from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import Iterable

import yaml

from custom_trainer.services.session_service import SessionInfo, discover_sessions, sync_legacy_labels
from custom_trainer.services.yolo_io import read_yolo_label_file, write_yolo_label_file


_DATASET_FILENAMES = ('dataset.yaml', 'data.yaml')
_TRAIN_LIST_NAME = 'train.txt'
_VAL_LIST_NAME = 'val.txt'
_CACHE_DIR_NAME = '.customtrainer_yolo_cache'
_CACHE_IMAGES_DIR = 'images'
_CACHE_LABELS_DIR = 'labels'


@dataclass(frozen=True)
class DatasetSummary:
    total_images: int
    train_images: int
    val_images: int
    labeled_images: int
    total_instances: int
    empty_or_missing_labels: int
    invalid_label_files: int
    migrated_labels: int
    cache_root: Path

    @property
    def has_usable_labels(self) -> bool:
        return self.total_instances > 0 and self.labeled_images > 0

    def describe(self) -> str:
        return (
            f'images={self.total_images} | train={self.train_images} | val={self.val_images} | '
            f'labeled_images={self.labeled_images} | instances={self.total_instances} | '
            f'empty_or_missing={self.empty_or_missing_labels} | invalid={self.invalid_label_files}'
        )



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



def _dataset_cache_root(root: Path) -> Path:
    return root / _CACHE_DIR_NAME



def _session_cache_prefix(session: SessionInfo) -> Path:
    safe_parts = [part for part in Path(session.name).parts if part not in ('', '.', '..')]
    return Path(*safe_parts) if safe_parts else Path(session.session_dir.name)



def _cache_image_path(cache_root: Path, session: SessionInfo, image_path: Path) -> Path:
    prefix = _session_cache_prefix(session)
    relative = session._relative_image_path(image_path)
    return cache_root / _CACHE_IMAGES_DIR / prefix / relative



def _cache_label_path(cache_root: Path, session: SessionInfo, image_path: Path) -> Path:
    prefix = _session_cache_prefix(session)
    relative = session._relative_image_path(image_path).with_suffix('.txt')
    return cache_root / _CACHE_LABELS_DIR / prefix / relative



def _link_or_copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        os.link(source, target)
        return
    except Exception:
        pass
    shutil.copy2(source, target)



def _build_dataset_spec(root: Path, class_names: Iterable[str]) -> tuple[dict, list[Path], list[Path], DatasetSummary]:
    sessions = discover_sessions(root)
    migrated_labels = sync_legacy_labels(sessions)
    image_paths = [image_path for session in sessions for image_path in session.image_paths]
    train_paths, val_paths = _split_image_paths(image_paths)
    if not train_paths and image_paths:
        train_paths = image_paths[:]
    if not val_paths:
        val_paths = train_paths[:] or image_paths[:]

    cache_root = _dataset_cache_root(root)
    shutil.rmtree(cache_root, ignore_errors=True)
    cache_root.mkdir(parents=True, exist_ok=True)

    cache_lookup: dict[Path, Path] = {}
    labeled_images = 0
    total_instances = 0
    empty_or_missing_labels = 0
    invalid_label_files = 0
    class_list = _normalize_class_names(class_names)
    class_count = len(class_list)

    for session in sessions:
        for image_path in session.image_paths:
            cache_image = _cache_image_path(cache_root, session, image_path)
            _link_or_copy_file(image_path, cache_image)
            cache_lookup[image_path] = cache_image

            canonical_label_path, _ = session.ensure_canonical_label_path(image_path)
            cache_label = _cache_label_path(cache_root, session, image_path)
            label_text = ''
            if canonical_label_path.exists() and canonical_label_path.is_file():
                try:
                    label_text = canonical_label_path.read_text(encoding='utf-8')
                except Exception:
                    label_text = ''
            boxes = [box for box in read_yolo_label_file(canonical_label_path) if 0 <= int(box.class_id) < class_count]
            has_raw_content = bool(label_text.strip())
            if boxes:
                write_yolo_label_file(cache_label, boxes)
                labeled_images += 1
                total_instances += len(boxes)
            elif has_raw_content:
                invalid_label_files += 1
            else:
                empty_or_missing_labels += 1

    train_cache_paths = [cache_lookup[path] for path in train_paths if path in cache_lookup]
    val_cache_paths = [cache_lookup[path] for path in val_paths if path in cache_lookup]

    _write_image_list(cache_root / _TRAIN_LIST_NAME, train_cache_paths)
    _write_image_list(cache_root / _VAL_LIST_NAME, val_cache_paths)

    spec = {
        'path': cache_root.resolve().as_posix(),
        'train': _TRAIN_LIST_NAME,
        'val': _VAL_LIST_NAME,
        'names': class_list,
        'nc': len(class_list),
    }
    summary = DatasetSummary(
        total_images=len(image_paths),
        train_images=len(train_cache_paths),
        val_images=len(val_cache_paths),
        labeled_images=labeled_images,
        total_instances=total_instances,
        empty_or_missing_labels=empty_or_missing_labels,
        invalid_label_files=invalid_label_files,
        migrated_labels=migrated_labels,
        cache_root=cache_root,
    )
    return spec, train_cache_paths, val_cache_paths, summary



def prepare_dataset_yaml(path: Path, class_names: Iterable[str]) -> tuple[Path, bool, DatasetSummary]:
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    spec, _train_paths, _val_paths, summary = _build_dataset_spec(path.parent, class_names)
    text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    previous = path.read_text(encoding='utf-8') if path.exists() else None
    if previous != text:
        path.write_text(text, encoding='utf-8')
    return path, created, summary



def write_dataset_yaml(path: Path, class_names: Iterable[str]) -> tuple[Path, bool]:
    result_path, created, _summary = prepare_dataset_yaml(path, class_names)
    return result_path, created



def ensure_dataset_yaml(root: Path | None, class_names: Iterable[str], overwrite: bool = False) -> tuple[Path | None, bool]:
    path, created, _summary = ensure_dataset_yaml_with_summary(root, class_names, overwrite=overwrite)
    return path, created



def ensure_dataset_yaml_with_summary(
    root: Path | None,
    class_names: Iterable[str],
    overwrite: bool = False,
) -> tuple[Path | None, bool, DatasetSummary | None]:
    if root is None:
        return None, False, None
    existing = find_dataset_yaml(root)
    preferred = default_dataset_yaml_path(root)
    path = existing or preferred
    if existing is not None and existing != preferred and not overwrite:
        return existing, False, None
    result_path, created, summary = prepare_dataset_yaml(path, class_names)
    return result_path, created, summary
