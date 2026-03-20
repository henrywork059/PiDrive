from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
VIDEO_SUFFIXES = {'.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg', '.wmv', '.webm', '.m4v', '.ts', '.asf', '.gif'}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES


def list_images(root: Path) -> list[Path]:
    return sorted(
        [path for path in root.rglob('*') if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda item: item.as_posix().lower(),
    )


def _images_inside(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return list_images(path)


def list_media(root: Path) -> list[Path]:
    return sorted(
        [path for path in root.rglob('*') if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES],
        key=lambda item: item.as_posix().lower(),
    )


def _direct_media_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(
        [child for child in path.iterdir() if child.is_file() and child.suffix.lower() in MEDIA_SUFFIXES],
        key=lambda item: item.as_posix().lower(),
    )


def resolve_prediction_source(path: Path) -> tuple[Path, str | None]:
    """Resolve a user-selected prediction source into a media path Ultralytics can read.

    The GUI may let the user choose a session folder whose frames live under ``images/``
    or another nested directory. Ultralytics prediction, however, expects the provided
    directory itself to directly contain media files. This helper normalizes common
    session-style layouts into a usable media root while keeping the original selection
    intact for the UI.
    """
    if not path.exists():
        return path, None
    if path.is_file():
        return path, None
    if _direct_media_files(path):
        return path, None

    ok, image_root = looks_like_session_dir(path)
    if ok and image_root is not None:
        if image_root != path:
            return image_root, f'Session folder auto-resolved to image folder: {image_root}'
        return path, None

    sessions = discover_sessions(path)
    if len(sessions) == 1:
        resolved = sessions[0].image_root
        if resolved != path:
            return resolved, f'Folder auto-resolved to discovered session images: {resolved}'
        return resolved, None

    media_paths = list_media(path)
    if media_paths:
        first_parent = media_paths[0].parent
        unique_parents = {item.parent.resolve() for item in media_paths}
        if len(unique_parents) == 1:
            return first_parent, f'Folder auto-resolved to media directory: {first_parent}'

    return path, None


def yolo_expected_label_path(image_path: Path) -> Path:
    """Return the canonical YOLO label path for an image path.

    Typical supported layouts:
    - dataset root: root/images/<session>/frame.jpg -> root/labels/<session>/frame.txt
    - single session: session/images/frame.jpg -> session/labels/frame.txt
    - flat session: session/frame.jpg -> session/labels/frame.txt
    """
    parent = image_path.parent
    stem_name = f'{image_path.stem}.txt'
    if parent.name.lower() == 'images':
        return parent.parent / 'labels' / stem_name

    parts = list(image_path.parts)
    for idx in range(len(parts) - 2, -1, -1):
        if parts[idx].lower() == 'images':
            patched = parts.copy()
            patched[idx] = 'labels'
            return Path(*patched).with_suffix('.txt')

    return parent / 'labels' / stem_name


def legacy_inline_labels_dir_path(image_path: Path) -> Path:
    return image_path.parent / 'labels' / f'{image_path.stem}.txt'


@dataclass
class SessionInfo:
    name: str
    session_dir: Path
    image_root: Path
    image_paths: list[Path]
    labels_root: Path

    def _relative_image_path(self, image_path: Path) -> Path:
        try:
            return image_path.relative_to(self.image_root)
        except ValueError:
            return Path(image_path.name)

    def label_path_for_image(self, image_path: Path) -> Path:
        relative = self._relative_image_path(image_path).with_suffix('.txt')
        return self.labels_root / relative

    def label_candidates_for_image(self, image_path: Path) -> list[Path]:
        relative = self._relative_image_path(image_path).with_suffix('.txt')
        canonical = self.label_path_for_image(image_path)
        candidates = [
            canonical,
            yolo_expected_label_path(image_path),
            self.labels_root / 'images' / relative,
            self.session_dir / 'labels' / relative,
            legacy_inline_labels_dir_path(image_path),
            image_path.with_suffix('.txt'),
        ]

        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = candidate.resolve().as_posix() if candidate.exists() else candidate.as_posix().lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def find_existing_label_path(self, image_path: Path) -> Path | None:
        for candidate in self.label_candidates_for_image(image_path):
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def ensure_canonical_label_path(self, image_path: Path) -> tuple[Path, bool]:
        canonical = self.label_path_for_image(image_path)
        if canonical.exists() and canonical.is_file():
            return canonical, False

        for candidate in self.label_candidates_for_image(image_path):
            if candidate == canonical or not candidate.exists() or not candidate.is_file():
                continue
            try:
                text = candidate.read_text(encoding='utf-8')
            except Exception:
                continue
            if not text.strip():
                continue
            canonical.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text(text, encoding='utf-8')
            return canonical, True
        return canonical, False

    @property
    def labeled_count(self) -> int:
        count = 0
        for image_path in self.image_paths:
            label_path = self.find_existing_label_path(image_path)
            if label_path is None:
                continue
            try:
                if label_path.read_text(encoding='utf-8').strip():
                    count += 1
            except Exception:
                continue
        return count


def looks_like_session_dir(path: Path) -> tuple[bool, Path | None]:
    if not path.is_dir():
        return False, None
    direct_image_files = sorted(
        [child for child in path.iterdir() if child.is_file() and child.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda item: item.as_posix().lower(),
    )
    if direct_image_files:
        return True, path
    images_dir = path / 'images'
    if images_dir.is_dir() and _images_inside(images_dir):
        return True, images_dir
    return False, None


def _build_session_info(name: str, session_dir: Path, image_root: Path, labels_root: Path) -> SessionInfo | None:
    image_paths = list_images(image_root)
    if not image_paths:
        return None
    return SessionInfo(
        name=name,
        session_dir=session_dir,
        image_root=image_root,
        image_paths=image_paths,
        labels_root=labels_root,
    )


def _discover_dataset_root_sessions(root: Path) -> list[SessionInfo]:
    images_root = root / 'images'
    if not images_root.is_dir():
        return []
    sessions: list[SessionInfo] = []
    for child in sorted(images_root.iterdir()):
        if not child.is_dir():
            continue
        ok, image_root = looks_like_session_dir(child)
        if not ok or image_root is None:
            continue
        relative_child = child.relative_to(images_root)
        labels_root = root / 'labels' / relative_child
        session = _build_session_info(relative_child.as_posix(), child, image_root, labels_root)
        if session is not None:
            sessions.append(session)
    return sessions


def discover_sessions(root: Path) -> list[SessionInfo]:
    dataset_style_sessions = _discover_dataset_root_sessions(root)
    if dataset_style_sessions:
        return dataset_style_sessions

    ok, image_root = looks_like_session_dir(root)
    if ok and image_root is not None:
        labels_root = root / 'labels'
        session = _build_session_info(root.name, root, image_root, labels_root)
        if session is not None:
            return [session]

    sessions: list[SessionInfo] = []
    seen: set[Path] = set()
    candidates = [child for child in sorted(root.iterdir()) if child.is_dir()]
    for candidate in candidates:
        ok, image_root = looks_like_session_dir(candidate)
        if not ok or image_root is None:
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        labels_root = candidate / 'labels'
        session = _build_session_info(candidate.name, candidate, image_root, labels_root)
        if session is None:
            continue
        sessions.append(session)
        seen.add(resolved)

    return sessions


def sync_legacy_labels(sessions: list[SessionInfo]) -> int:
    migrated = 0
    for session in sessions:
        for image_path in session.image_paths:
            _, copied = session.ensure_canonical_label_path(image_path)
            if copied:
                migrated += 1
    return migrated


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
    text = "\n".join(name.strip() for name in class_names if name.strip())
    if text:
        text += "\n"
    path.write_text(text, encoding='utf-8')
    return path
