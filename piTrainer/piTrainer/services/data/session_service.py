from __future__ import annotations

from pathlib import Path



def list_sessions(records_root: Path) -> list[str]:
    if not records_root.exists() or not records_root.is_dir():
        return []
    sessions: list[str] = []
    for entry in sorted(records_root.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "records.jsonl").exists() and (entry / "images").exists():
            sessions.append(entry.name)
    return sessions
