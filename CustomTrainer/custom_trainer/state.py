from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from custom_trainer.services.dataset_service import default_dataset_yaml_path, find_dataset_yaml
from custom_trainer.services.session_service import SessionInfo


@dataclass
class AppState:
    sessions_root: Path | None = None
    sessions: list[SessionInfo] = field(default_factory=list)
    current_session_index: int = -1
    current_image_index: int = -1
    class_names: list[str] = field(default_factory=lambda: ['object'])

    @property
    def current_session(self) -> SessionInfo | None:
        if 0 <= self.current_session_index < len(self.sessions):
            return self.sessions[self.current_session_index]
        return None

    @property
    def current_image_path(self) -> Path | None:
        session = self.current_session
        if session is None:
            return None
        if 0 <= self.current_image_index < len(session.image_paths):
            return session.image_paths[self.current_image_index]
        return None

    def current_preview_image(self) -> Path | None:
        image_path = self.current_image_path
        if image_path is not None:
            return image_path
        session = self.current_session
        if session is not None and session.image_paths:
            return session.image_paths[0]
        for session in self.sessions:
            if session.image_paths:
                return session.image_paths[0]
        return None

    def preferred_dataset_yaml(self) -> Path | None:
        if self.sessions_root is None:
            return None
        existing = find_dataset_yaml(self.sessions_root)
        if existing is not None:
            return existing
        return default_dataset_yaml_path(self.sessions_root)

    def latest_best_weights(self) -> Path | None:
        search_roots: list[Path] = []
        if self.sessions_root is not None:
            search_roots.append(self.sessions_root)
        session = self.current_session
        if session is not None:
            search_roots.append(session.session_dir)
        candidates: list[Path] = []
        seen: set[str] = set()
        for root in search_roots:
            key = root.resolve().as_posix() if root.exists() else root.as_posix().lower()
            if key in seen or not root.exists():
                continue
            seen.add(key)
            candidates.extend(path for path in root.rglob('best.pt') if path.is_file())
        if not candidates:
            return None
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return candidates[0]
