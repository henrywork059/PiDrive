from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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
