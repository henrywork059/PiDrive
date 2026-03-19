from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_STATE_FILENAME = 'ui_state.json'


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def state_file_path() -> Path:
    return _project_root() / 'config' / _STATE_FILENAME


def _default_state() -> dict[str, Any]:
    return {
        'last_sessions_root': '',
        'window_geometry': '',
        'window_state': '',
        'splitters': {},
    }


def load_ui_state() -> dict[str, Any]:
    path = state_file_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                merged = _default_state()
                merged.update(data)
                if not isinstance(merged.get('splitters'), dict):
                    merged['splitters'] = {}
                return merged
    except Exception:
        pass
    return _default_state()


def save_ui_state(data: dict[str, Any]) -> Path:
    merged = _default_state()
    merged.update(data or {})
    if not isinstance(merged.get('splitters'), dict):
        merged['splitters'] = {}
    path = state_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix('.tmp')
    temp_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding='utf-8')
    temp_path.replace(path)
    return path


def get_last_sessions_root() -> Path | None:
    raw = str(load_ui_state().get('last_sessions_root', '') or '').strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path


def set_last_sessions_root(path: str | Path | None) -> None:
    state = load_ui_state()
    state['last_sessions_root'] = str(Path(path).expanduser()) if path else ''
    save_ui_state(state)


def get_splitter_state(name: str) -> list[int] | None:
    splitters = load_ui_state().get('splitters', {})
    values = splitters.get(name)
    if not isinstance(values, list):
        return None
    result: list[int] = []
    for value in values:
        try:
            result.append(max(0, int(value)))
        except Exception:
            continue
    return result or None


def set_splitter_state(name: str, sizes: list[int]) -> None:
    state = load_ui_state()
    splitters = state.setdefault('splitters', {})
    if not isinstance(splitters, dict):
        splitters = {}
        state['splitters'] = splitters
    splitters[name] = [max(0, int(value)) for value in sizes]
    save_ui_state(state)
