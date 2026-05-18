from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .record_loader_service import IMAGE_KEYS, coalesce_value
from .session_service import resolve_session_dir

TS_KEYS = ['ts', 'timestamp', 'timestamp_utc', 'saved_at_utc']
ID_KEYS = ['frame_id', 'id', 'source_frame_seq']


def _record_image_name(record: dict[str, Any]) -> str:
    image_value = coalesce_value(record, IMAGE_KEYS, '')
    return Path(str(image_value or '')).name


def _record_ts(record: dict[str, Any]) -> str:
    return str(coalesce_value(record, TS_KEYS, '') or '')


def _record_id(record: dict[str, Any]) -> str:
    return str(coalesce_value(record, ID_KEYS, '') or '')


def _line_matches(record: dict, frame_id: str, image_name: str, ts: str) -> bool:
    id_match = bool(frame_id) and _record_id(record) == str(frame_id)
    image_match = bool(image_name) and _record_image_name(record) == str(image_name)
    ts_match = bool(ts) and _record_ts(record) == str(ts)
    if id_match and (image_match or ts_match):
        return True
    if image_match and ts_match:
        return True
    return False


def _with_newline(raw_line: str) -> str:
    return raw_line if raw_line.endswith('\n') else raw_line + '\n'


def _delete_from_jsonl(path: Path, *, frame_id: str, image_name: str, ts: str) -> bool:
    if not path.exists():
        return False
    kept_lines: list[str] = []
    deleted = False
    with path.open('r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                kept_lines.append(_with_newline(raw_line))
                continue
            if not deleted and isinstance(record, dict) and _line_matches(record, frame_id=frame_id, image_name=image_name, ts=ts):
                deleted = True
                continue
            kept_lines.append(_with_newline(raw_line))
    if deleted:
        with path.open('w', encoding='utf-8') as handle:
            handle.writelines(kept_lines)
    return deleted


def delete_frame_from_session(records_root: Path, session_name: str, frame_id: str, image_path: str, ts: str = '') -> tuple[bool, str]:
    session_dir = resolve_session_dir(records_root, session_name)
    image_name = Path(image_path).name

    labels_deleted = _delete_from_jsonl(session_dir / 'labels.jsonl', frame_id=frame_id, image_name=image_name, ts=ts)
    records_deleted = _delete_from_jsonl(session_dir / 'records.jsonl', frame_id=frame_id, image_name=image_name, ts=ts)

    if not labels_deleted and not records_deleted:
        return False, f"Could not find frame '{frame_id}' in session '{session_name}'."

    if image_path:
        try:
            image_file = Path(image_path)
            if image_file.exists():
                image_file.unlink()
        except OSError as exc:
            return True, f"Frame metadata deleted, but image file could not be removed: {exc}"

    targets = []
    if labels_deleted:
        targets.append('labels.jsonl')
    if records_deleted:
        targets.append('records.jsonl')
    return True, f"Deleted frame '{frame_id}' from {', '.join(targets)}."
