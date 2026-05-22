from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .record_loader_service import IMAGE_KEYS
from .session_service import resolve_session_dir
from .visibility_service import is_record_hidden, mark_record_hidden, utc_timestamp

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


def _target_from_record(record: dict[str, Any]) -> dict[str, str]:
    return {
        'session': str(record.get('session', '') or ''),
        'frame_id': str(record.get('frame_id', '') or ''),
        'image_name': Path(str(record.get('abs_image', '') or record.get('image_path', '') or '')).name,
        'ts': str(record.get('ts', '') or ''),
    }


def _target_key(target: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        str(target.get('session', '')),
        str(target.get('frame_id', '')),
        str(target.get('image_name', '')),
        str(target.get('ts', '')),
    )


def _target_label(target: dict[str, str]) -> str:
    frame_id = str(target.get('frame_id', '')).strip()
    image_name = str(target.get('image_name', '')).strip()
    ts = str(target.get('ts', '')).strip()
    if frame_id:
        return frame_id
    if image_name:
        return image_name
    return ts or 'unknown frame'


def _matching_target(record: dict[str, Any], targets: list[dict[str, str]]) -> dict[str, str] | None:
    for target in targets:
        if _line_matches(
            record,
            frame_id=str(target.get('frame_id', '')),
            image_name=str(target.get('image_name', '')),
            ts=str(target.get('ts', '')),
        ):
            return target
    return None


def _hide_in_jsonl(path: Path, targets: list[dict[str, str]], *, hidden_at_utc: str) -> tuple[int, set[tuple[str, str, str, str]]]:
    if not path.exists() or not targets:
        return 0, set()

    changed_rows = 0
    matched_targets: set[tuple[str, str, str, str]] = set()
    output_lines: list[str] = []
    with path.open('r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                output_lines.append(_with_newline(raw_line))
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                output_lines.append(_with_newline(raw_line))
                continue

            if isinstance(record, dict):
                target = _matching_target(record, targets)
                if target is not None:
                    matched_targets.add(_target_key(target))
                    if not is_record_hidden(record):
                        mark_record_hidden(record, hidden_at_utc=hidden_at_utc)
                        changed_rows += 1
                        output_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
                        continue

            output_lines.append(_with_newline(raw_line))

    if changed_rows:
        with path.open('w', encoding='utf-8') as handle:
            handle.writelines(output_lines)
    return changed_rows, matched_targets


def hide_frames_from_training(records_root: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Soft-delete selected frame rows by adding traceable hidden flags.

    This keeps labels.jsonl/records.jsonl rows and image files in place, so the
    action is fast and auditable. Hidden records are skipped by the loader and
    final training/validation guards.
    """
    targets_by_session: dict[str, list[dict[str, str]]] = {}
    selected_keys: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for record in records:
        target = _target_from_record(record)
        session_name = target['session'].strip()
        key = _target_key(target)
        if not session_name or key in selected_keys:
            continue
        selected_keys[key] = target
        targets_by_session.setdefault(session_name, []).append(target)

    hidden_at = utc_timestamp()
    matched_keys: set[tuple[str, str, str, str]] = set()
    metadata_rows_changed = 0
    files_changed: list[str] = []

    for session_name, targets in targets_by_session.items():
        session_dir = resolve_session_dir(records_root, session_name)
        for filename in ('labels.jsonl', 'records.jsonl'):
            path = session_dir / filename
            changed_rows, file_matches = _hide_in_jsonl(path, targets, hidden_at_utc=hidden_at)
            if changed_rows:
                files_changed.append(f'{session_name}/{filename}')
            metadata_rows_changed += changed_rows
            matched_keys.update(file_matches)

    failed_messages = [
        f"Could not find frame '{_target_label(target)}' in session '{target.get('session', '')}'."
        for key, target in selected_keys.items()
        if key not in matched_keys
    ]

    return {
        'selected_count': len(selected_keys),
        'hidden_count': len(matched_keys),
        'metadata_rows_changed': metadata_rows_changed,
        'files_changed': files_changed,
        'failed_messages': failed_messages,
        'hidden_at_utc': hidden_at,
    }


def delete_frame_from_session(records_root: Path, session_name: str, frame_id: str, image_path: str, ts: str = '') -> tuple[bool, str]:
    """Backward-compatible wrapper: now soft-deletes by hiding from training."""
    result = hide_frames_from_training(records_root, [{
        'session': session_name,
        'frame_id': frame_id,
        'abs_image': image_path,
        'ts': ts,
    }])
    if result['hidden_count'] <= 0:
        failures = result.get('failed_messages') or [f"Could not find frame '{frame_id}' in session '{session_name}'."]
        return False, failures[0]
    rows = int(result.get('metadata_rows_changed', 0))
    return True, f"Hidden frame '{frame_id}' from training with traceable flags in {rows} metadata row(s). Image file was kept."
