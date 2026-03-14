from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


@dataclass
class SessionInfo:
    name: str
    session_dir: Path
    image_root: Path
    image_paths: list[Path]
    labels_root: Path

    @property
    def labeled_count(self) -> int:
        return sum(1 for image_path in self.image_paths if self.label_path_for_image(image_path).exists())

    def label_path_for_image(self, image_path: Path) -> Path:
        sidecar = image_path.with_suffix('.txt')
        mirrored = self.labels_root / image_path.relative_to(self.image_root)
        mirrored = mirrored.with_suffix('.txt')
        if mirrored.exists():
            return mirrored
        if sidecar.exists():
            return sidecar
        return mirrored


def list_images(root: Path) -> list[Path]:
    return sorted(
        [path for path in root.rglob('*') if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda item: item.as_posix().lower(),
    )


def looks_like_session_dir(path: Path) -> tuple[bool, Path | None]:
    if not path.is_dir():
        return False, None
    direct_images = list_images(path)
    if direct_images:
        return True, path
    images_dir = path / 'images'
    if images_dir.is_dir() and list_images(images_dir):
        return True, images_dir
    return False, None


def discover_sessions(root: Path) -> list[SessionInfo]:
    sessions: list[SessionInfo] = []
    seen: set[Path] = set()
    candidates = [root] + [child for child in sorted(root.iterdir()) if child.is_dir()]
    for candidate in candidates:
        ok, image_root = looks_like_session_dir(candidate)
        if not ok or image_root is None:
            continue
        session_dir = candidate
        if session_dir.resolve() in seen:
            continue
        image_paths = list_images(image_root)
        if not image_paths:
            continue
        labels_root = session_dir / 'labels'
        sessions.append(
            SessionInfo(
                name=session_dir.name,
                session_dir=session_dir,
                image_root=image_root,
                image_paths=image_paths,
                labels_root=labels_root,
            )
        )
        seen.add(session_dir.resolve())
    return sessions


def load_class_names(root_hint: Path | None, session: SessionInfo | None) -> list[str]:
    search_paths: list[Path] = []
    if root_hint is not None:
        search_paths.extend([root_hint / 'classes.txt', root_hint / 'dataset.yaml', root_hint / 'data.yaml'])
    if session is not None:
        search_paths.extend(
            [
                session.session_dir / 'classes.txt',
                session.session_dir / 'dataset.yaml',
                session.session_dir / 'data.yaml',
                session.session_dir.parent / 'classes.txt',
                session.session_dir.parent / 'dataset.yaml',
                session.session_dir.parent / 'data.yaml',
            ]
        )
    for path in search_paths:
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() == '.txt':
            names = [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            if names:
                return names
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        names = data.get('names') if isinstance(data, dict) else None
        if isinstance(names, list):
            clean = [str(item).strip() for item in names if str(item).strip()]
            if clean:
                return clean
        if isinstance(names, dict):
            ordered = [str(names[key]).strip() for key in sorted(names) if str(names[key]).strip()]
            if ordered:
                return ordered
    return ['object']


def save_class_names(target_dir: Path, class_names: list[str]) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / 'classes.txt'
    text = '\n'.join(name.strip() for name in class_names if name.strip())
    if text:
        text += '\n'
    path.write_text(text, encoding='utf-8')
    return path
