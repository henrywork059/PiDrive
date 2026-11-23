from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import shutil
from typing import Iterable

import yaml

from custom_trainer.services.cache_lifecycle import (
    new_cache_generation, publish_cache_generation, atomic_write_yaml,
)
from custom_trainer.services.session_service import SessionInfo, discover_sessions, sync_legacy_labels
from custom_trainer.services.yolo_io import validate_yolo_label_file, write_yolo_label_file


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
    cache_yaml_path: Path | None = None
    train_labeled_images: int = 0
    val_labeled_images: int = 0
    duplicate_images: int = 0
    invalid_annotations: int = 0
    session_quality: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    annotation_issues: tuple[str, ...] = ()

    @property
    def has_validation_holdout(self) -> bool:
        return self.train_images > 0 and self.val_images > 0

    @property
    def has_usable_labels(self) -> bool:
        return self.total_instances > 0 and self.train_labeled_images > 0

    def describe(self) -> str:
        return (
            f'images={self.total_images} | train={self.train_images} | val={self.val_images} | '
            f'labeled_images={self.labeled_images} | instances={self.total_instances} | '
            f'empty_or_missing={self.empty_or_missing_labels} | invalid={self.invalid_label_files} | '
            f'invalid_boxes={self.invalid_annotations} | duplicates={self.duplicate_images} | '
            f'train_labeled={self.train_labeled_images} | val_labeled={self.val_labeled_images} | '
            f'holdout={"yes" if self.has_validation_holdout else "no"}'
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



def _image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _split_image_paths(
    image_paths: list[Path], sessions: list[SessionInfo] | None = None,
) -> tuple[list[Path], list[Path], int]:
    """Split full capture sessions, connecting sessions with identical image bytes.

    Never manufacture validation examples when there is only one independent
    session/content group. Source file names alone do not prove uniqueness.
    """
    ordered = sorted(image_paths, key=lambda p: p.as_posix().lower())
    if not ordered:
        return [], [], 0
    if sessions is None:
        # Backward-compatible helper use: treat parent folders as sessions.
        group_names = {p: p.parent.as_posix() for p in ordered}
    else:
        group_names = {p: session.name for session in sessions for p in session.image_paths}
    names = sorted(set(group_names.values()))
    parents = {name: name for name in names}

    def find(name: str) -> str:
        while parents[name] != name:
            parents[name] = parents[parents[name]]
            name = parents[name]
        return name

    def union(one: str, two: str) -> None:
        roots = find(one), find(two)
        if roots[0] != roots[1]:
            parents[max(roots)] = min(roots)

    fingerprints: dict[str, str] = {}
    duplicate_images = 0
    for path in ordered:
        digest = _image_sha256(path)
        owner = group_names[path]
        if digest in fingerprints:
            duplicate_images += 1
            union(owner, fingerprints[digest])
        else:
            fingerprints[digest] = owner
    clusters: dict[str, list[Path]] = {}
    for path in ordered:
        clusters.setdefault(find(group_names[path]), []).append(path)
    if len(clusters) < 2:
        return ordered, [], duplicate_images

    target_count = max(1, round(len(ordered) * 0.10))
    group_keys = sorted(clusters)
    # Deterministic approximate 10% holdout. Never split a session/content
    # family merely to achieve the requested percentage exactly.
    candidates = sorted(group_keys, key=lambda key: (abs(len(clusters[key]) - target_count), key))
    val_groups = {candidates[0]}
    val_count = len(clusters[candidates[0]])
    for key in candidates[1:]:
        size = len(clusters[key])
        if len(val_groups) >= len(clusters) - 1:
            break
        if abs(target_count - val_count - size) < abs(target_count - val_count):
            val_groups.add(key)
            val_count += size
    val_paths = [p for p in ordered if find(group_names[p]) in val_groups]
    train_paths = [p for p in ordered if find(group_names[p]) not in val_groups]
    assert not set(train_paths) & set(val_paths)
    return train_paths, val_paths, duplicate_images


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
    # Snapshot bytes, not a hard link: editing a source image in place must
    # never change a generation that an active YOLO task already references.
    shutil.copy2(source, target)



def _build_dataset_spec_staged(
    root: Path, class_names: Iterable[str], staged_root: Path, cache_root: Path,
) -> tuple[dict, list[Path], list[Path], DatasetSummary]:
    sessions = discover_sessions(root)
    migrated_labels = sync_legacy_labels(sessions)
    image_paths = [image_path for session in sessions for image_path in session.image_paths]
    train_paths, val_paths, duplicate_images = _split_image_paths(image_paths, sessions)

    # The published path is used in the lists, but all files are written to
    # a private staging directory until validation and atomic promotion.

    cache_lookup: dict[Path, Path] = {}
    labeled_images = 0
    total_instances = 0
    empty_or_missing_labels = 0
    invalid_label_files = 0
    invalid_annotations = 0
    session_quality: list[str] = []
    annotation_issues: list[str] = []
    warnings: list[str] = []
    if image_paths and not val_paths:
        warnings.append('No independent validation holdout: add another non-duplicate capture session before training/validation.')
    if duplicate_images:
        warnings.append(f'{duplicate_images} duplicate image(s) found; linked sessions kept in one split.')
    labeled_paths: set[Path] = set()
    class_list = _normalize_class_names(class_names)
    class_count = len(class_list)

    for session in sessions:
        session_labeled = session_instances = session_empty = session_invalid_files = session_invalid_rows = 0
        for image_path in session.image_paths:
            cache_image = _cache_image_path(staged_root, session, image_path)
            _link_or_copy_file(image_path, cache_image)
            cache_lookup[image_path] = _cache_image_path(cache_root, session, image_path)

            canonical_label_path, _ = session.ensure_canonical_label_path(image_path)
            cache_label = _cache_label_path(staged_root, session, image_path)
            label_text = ''
            if canonical_label_path.exists() and canonical_label_path.is_file():
                try:
                    label_text = canonical_label_path.read_text(encoding='utf-8')
                except Exception:
                    label_text = ''
            boxes, issues = validate_yolo_label_file(canonical_label_path, class_count)
            # An existing file with unreadable content is a validation error,
            # not an empty, successfully labeled frame.
            if issues:
                invalid_label_files += 1
                invalid_annotations += len(issues)
                session_invalid_files += 1
                session_invalid_rows += len(issues)
                for issue in issues:
                    if len(annotation_issues) < 40:
                        annotation_issues.append(
                            f'{session.name}/{image_path.name} line {issue.line}: {issue.reason}'
                        )
            if boxes:
                write_yolo_label_file(cache_label, boxes)
                labeled_images += 1
                labeled_paths.add(image_path)
                total_instances += len(boxes)
                session_labeled += 1
                session_instances += len(boxes)
            elif not issues and not label_text.strip():
                empty_or_missing_labels += 1
                session_empty += 1
        session_quality.append(
            f'{session.name}: images={len(session.image_paths)}, labeled={session_labeled}, '
            f'boxes={session_instances}, empty={session_empty}, '
            f'invalid_files={session_invalid_files}, invalid_boxes={session_invalid_rows}'
        )
    if invalid_annotations:
        warnings.append(f'{invalid_annotations} invalid annotation line(s) excluded from generated training labels; source labels unchanged.')

    train_labeled_images = sum(path in labeled_paths for path in train_paths)
    val_labeled_images = sum(path in labeled_paths for path in val_paths)
    if train_paths and not train_labeled_images:
        warnings.append('No valid training labels in selected training sessions; add boxes or more independent sessions.')
    if val_paths and not val_labeled_images:
        warnings.append('Validation has no labeled positive examples; its detection metrics may be uninformative.')
    train_cache_paths = [cache_lookup[path] for path in train_paths if path in cache_lookup]
    val_cache_paths = [cache_lookup[path] for path in val_paths if path in cache_lookup]

    _write_image_list(staged_root / _TRAIN_LIST_NAME, train_cache_paths)
    _write_image_list(staged_root / _VAL_LIST_NAME, val_cache_paths)

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
        cache_yaml_path=cache_root / 'dataset.yaml',
        train_labeled_images=train_labeled_images,
        val_labeled_images=val_labeled_images,
        duplicate_images=duplicate_images,
        invalid_annotations=invalid_annotations,
        session_quality=tuple(session_quality),
        warnings=tuple(warnings),
        annotation_issues=tuple(annotation_issues),
    )
    return spec, train_cache_paths, val_cache_paths, summary



def _build_dataset_spec(root: Path, class_names: Iterable[str]) -> tuple[dict, list[Path], list[Path], DatasetSummary]:
    staged, published = new_cache_generation(root)
    try:
        spec, train, val, summary = _build_dataset_spec_staged(root, class_names, staged, published)
        publish_cache_generation(staged, published, spec,
                                 image_count=summary.total_images, valid_labels=summary.labeled_images)
        return spec, train, val, summary
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def prepare_dataset_yaml(path: Path, class_names: Iterable[str]) -> tuple[Path, bool, DatasetSummary]:
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    spec, _train_paths, _val_paths, summary = _build_dataset_spec(path.parent, class_names)
    text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    previous = path.read_text(encoding='utf-8') if path.exists() else None
    if previous != text:
        atomic_write_yaml(path, spec)
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
