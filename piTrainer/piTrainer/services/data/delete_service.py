from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .record_loader_service import IMAGE_KEYS
from .session_service import resolve_session_dir

TS_KEYS = ['ts', 'timestamp', 'timestamp_utc', 'saved_at_utc']
ID_KEYS = ['frame_id', 'id', 'source_frame_seq']


def _training_label(record: dict[str, Any]) -> dict[str, Any]:
    training_label = record.get('training_label')
    return training_label if isinstance(training_label, dict) else {}


def _candidate_values(record: dict[str, Any], keys: list[str]) -> list[Any]:
    values: list[Any] = []
    nested = _training_label(record)
    for source in (record, nested):
        for key in keys:
            if key in source and source[key] is not None:
                values.append(source[key])
    return values


def _record_image_names(record: dict[str, Any]) -> set[str]:
    return {Path(str(value or '')).name for value in _candidate_values(record, IMAGE_KEYS) if str(value or '').strip()}


def _record_timestamps(record: dict[str, Any]) -> set[str]:
    return {str(value or '') for value in _candidate_values(record, TS_KEYS) if str(value or '').strip()}


def _record_ids(record: dict[str, Any]) -> set[str]:
    return {str(value or '') for value in _candidate_values(record, ID_KEYS) if str(value or '').strip()}


def _line_matches(record: dict, frame_id: str, image_name: str, ts: str) -> bool:
    ids = _record_ids(record)
    image_names = _record_image_names(record)
    timestamps = _record_timestamps(record)
    id_match = bool(frame_id) and str(frame_id) in ids
    image_match = bool(image_name) and str(image_name) in image_names
    ts_match = bool(ts) and str(ts) in timestamps
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
