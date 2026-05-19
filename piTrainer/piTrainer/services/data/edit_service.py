from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .record_loader_service import IMAGE_KEYS, STEER_KEYS, THROTTLE_KEYS
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

    # PiSD labels.jsonl rows usually have source_frame_seq + timestamp_utc + frame.
    # PiSD records.jsonl rows may keep those same identifiers inside training_label.
    if id_match and (image_match or ts_match):
        return True
    if image_match and ts_match:
        return True
    return False


def _first_existing_key(record: dict, keys: list[str], fallback: str) -> str:
    for key in keys:
        if key in record:
            return key
    return fallback


def _with_newline(raw_line: str) -> str:
    return raw_line if raw_line.endswith('\n') else raw_line + '\n'


def _update_jsonl_file(path: Path, *, frame_id: str, image_name: str, ts: str, steering: float, throttle: float) -> bool:
    if not path.exists():
        return False

    updated = False
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

            if not updated and isinstance(record, dict) and _line_matches(record, frame_id=frame_id, image_name=image_name, ts=ts):
                steer_key = _first_existing_key(record, STEER_KEYS, 'steering')
                throttle_key = _first_existing_key(record, THROTTLE_KEYS, 'throttle')
                record[steer_key] = float(steering)
                record[throttle_key] = float(throttle)
                training_label = record.get('training_label')
                if isinstance(training_label, dict):
                    training_label['steering'] = float(steering)
                    training_label['throttle'] = float(throttle)
                updated = True
                output_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
                continue

            output_lines.append(_with_newline(raw_line))

    if updated:
        with path.open('w', encoding='utf-8') as handle:
            handle.writelines(output_lines)
    return updated


def update_frame_controls(
    records_root: Path,
    session_name: str,
    frame_id: str,
    image_path: str,
    ts: str,
    steering: float,
    throttle: float,
) -> tuple[bool, str]:
    session_dir = resolve_session_dir(records_root, session_name)
    image_name = Path(image_path).name

    labels_updated = _update_jsonl_file(
        session_dir / 'labels.jsonl',
        frame_id=frame_id,
        image_name=image_name,
        ts=ts,
        steering=steering,
        throttle=throttle,
    )
    records_updated = _update_jsonl_file(
        session_dir / 'records.jsonl',
        frame_id=frame_id,
        image_name=image_name,
        ts=ts,
        steering=steering,
        throttle=throttle,
    )

    if not labels_updated and not records_updated:
        return False, f"Could not find frame '{frame_id}' in session '{session_name}'."

    targets = []
    if labels_updated:
        targets.append('labels.jsonl')
    if records_updated:
        targets.append('records.jsonl')
    return True, f"Updated steering/speed for frame '{frame_id}' in {', '.join(targets)}."
