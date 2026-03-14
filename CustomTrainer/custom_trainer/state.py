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

    def preferred_dataset_yaml(self) -> Path | None:
        if self.sessions_root is None:
            return None
        existing = find_dataset_yaml(self.sessions_root)
        if existing is not None:
            return existing
        return default_dataset_yaml_path(self.sessions_root)
