from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .record_loader_service import IMAGE_KEYS, STEER_KEYS, THROTTLE_KEYS
from .session_service import resolve_session_dir

TS_KEYS = ['ts', 'timestamp', 'timestamp_utc', 'saved_at_utc']
ID_KEYS = ['frame_id', 'id', 'source_frame_seq']


TargetKey = tuple[str, str, str, str]


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
    return _line_matches_values(
        ids=ids,
        image_names=image_names,
        timestamps=timestamps,
        frame_id=frame_id,
        image_name=image_name,
        ts=ts,
    )


def _line_matches_values(
    *,
    ids: set[str],
    image_names: set[str],
    timestamps: set[str],
    frame_id: str,
    image_name: str,
    ts: str,
) -> bool:
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


def _target_from_record(record: dict[str, Any]) -> dict[str, str]:
    return {
        'session': str(record.get('session', '') or ''),
        'frame_id': str(record.get('frame_id', '') or ''),
        'image_name': Path(str(record.get('abs_image', '') or record.get('image_path', '') or record.get('frame', '') or '')).name,
        'ts': str(record.get('ts', '') or ''),
    }


def _target_key(target: dict[str, str]) -> TargetKey:
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


def _apply_record_control_update(
    record: dict[str, Any],
    *,
    steering: float,
    throttle: float,
    update_steering: bool = True,
    update_throttle: bool = True,
) -> None:
    if update_steering:
        steer_key = _first_existing_key(record, STEER_KEYS, 'steering')
        record[steer_key] = float(steering)
    if update_throttle:
        throttle_key = _first_existing_key(record, THROTTLE_KEYS, 'throttle')
        record[throttle_key] = float(throttle)
    training_label = record.get('training_label')
    if isinstance(training_label, dict):
        if update_steering:
            training_label['steering'] = float(steering)
        if update_throttle:
            training_label['throttle'] = float(throttle)


def _update_jsonl_file(
    path: Path,
    *,
    frame_id: str,
    image_name: str,
    ts: str,
    steering: float,
    throttle: float,
    update_steering: bool = True,
    update_throttle: bool = True,
) -> bool:
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
                _apply_record_control_update(
                    record,
                    steering=steering,
                    throttle=throttle,
                    update_steering=update_steering,
                    update_throttle=update_throttle,
                )
                updated = True
                output_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
                continue

            output_lines.append(_with_newline(raw_line))

    if updated:
        with path.open('w', encoding='utf-8') as handle:
            handle.writelines(output_lines)
    return updated


def _build_target_indexes(targets: list[dict[str, str]]) -> tuple[dict[TargetKey, dict[str, str]], dict[str, set[TargetKey]], dict[str, set[TargetKey]], dict[str, set[TargetKey]]]:
    target_by_key: dict[TargetKey, dict[str, str]] = {}
    by_id: dict[str, set[TargetKey]] = {}
    by_image: dict[str, set[TargetKey]] = {}
    by_ts: dict[str, set[TargetKey]] = {}

    for target in targets:
        key = _target_key(target)
        target_by_key[key] = target
        frame_id = str(target.get('frame_id', '')).strip()
        image_name = str(target.get('image_name', '')).strip()
        ts = str(target.get('ts', '')).strip()
        if frame_id:
            by_id.setdefault(frame_id, set()).add(key)
        if image_name:
            by_image.setdefault(image_name, set()).add(key)
        if ts:
            by_ts.setdefault(ts, set()).add(key)
    return target_by_key, by_id, by_image, by_ts


def _matching_indexed_target(
    record: dict[str, Any],
    *,
    target_by_key: dict[TargetKey, dict[str, str]],
    by_id: dict[str, set[TargetKey]],
    by_image: dict[str, set[TargetKey]],
    by_ts: dict[str, set[TargetKey]],
    already_matched: set[TargetKey],
) -> TargetKey | None:
    ids = _record_ids(record)
    image_names = _record_image_names(record)
    timestamps = _record_timestamps(record)

    candidate_keys: set[TargetKey] = set()
    for value in ids:
        candidate_keys.update(by_id.get(value, set()))
    for value in image_names:
        candidate_keys.update(by_image.get(value, set()))
    for value in timestamps:
        candidate_keys.update(by_ts.get(value, set()))

    for key in candidate_keys:
        if key in already_matched:
            continue
        target = target_by_key[key]
        if _line_matches_values(
            ids=ids,
            image_names=image_names,
            timestamps=timestamps,
            frame_id=str(target.get('frame_id', '')),
            image_name=str(target.get('image_name', '')),
            ts=str(target.get('ts', '')),
        ):
            return key
    return None


def _update_jsonl_file_batch(
    path: Path,
    targets: list[dict[str, str]],
    *,
    steering: float,
    throttle: float,
    update_steering: bool = True,
    update_throttle: bool = True,
) -> tuple[int, set[TargetKey]]:
    """Update all matching selected rows in one JSONL scan.

    The previous bulk-edit path called the single-frame updater once per row,
    which rewrote labels.jsonl and records.jsonl repeatedly. This batch path
    keeps matching indexed by stable row identifiers, scans each metadata file
    once, and rewrites only when something changed.
    """
    if not path.exists() or not targets:
        return 0, set()

    target_by_key, by_id, by_image, by_ts = _build_target_indexes(targets)
    matched_targets: set[TargetKey] = set()
    changed_rows = 0
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
                key = _matching_indexed_target(
                    record,
                    target_by_key=target_by_key,
                    by_id=by_id,
                    by_image=by_image,
                    by_ts=by_ts,
                    already_matched=matched_targets,
                )
                if key is not None:
                    _apply_record_control_update(
                        record,
                        steering=steering,
                        throttle=throttle,
                        update_steering=update_steering,
                        update_throttle=update_throttle,
                    )
                    matched_targets.add(key)
                    changed_rows += 1
                    output_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
                    continue

            output_lines.append(_with_newline(raw_line))

    if changed_rows:
        with path.open('w', encoding='utf-8') as handle:
            handle.writelines(output_lines)
    return changed_rows, matched_targets


def update_frame_controls(
    records_root: Path,
    session_name: str,
    frame_id: str,
    image_path: str,
    ts: str,
    steering: float,
    throttle: float,
    update_steering: bool = True,
    update_throttle: bool = True,
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
        update_steering=update_steering,
        update_throttle=update_throttle,
    )
    records_updated = _update_jsonl_file(
        session_dir / 'records.jsonl',
        frame_id=frame_id,
        image_name=image_name,
        ts=ts,
        steering=steering,
        throttle=throttle,
        update_steering=update_steering,
        update_throttle=update_throttle,
    )

    if not labels_updated and not records_updated:
        return False, f"Could not find frame '{frame_id}' in session '{session_name}'."

    targets = []
    if labels_updated:
        targets.append('labels.jsonl')
    if records_updated:
        targets.append('records.jsonl')
    changed_fields = []
    if update_steering:
        changed_fields.append('steering')
    if update_throttle:
        changed_fields.append('speed')
    field_label = '/'.join(changed_fields) if changed_fields else 'controls'
    return True, f"Updated {field_label} for frame '{frame_id}' in {', '.join(targets)}."


def update_frame_controls_batch(
    records_root: Path,
    records: Iterable[dict[str, Any]],
    *,
    steering: float,
    throttle: float,
    update_steering: bool = True,
    update_throttle: bool = True,
) -> dict[str, Any]:
    """Batch-update selected frame controls with one scan per session metadata file."""
    targets_by_session: dict[str, list[dict[str, str]]] = {}
    selected_targets: dict[TargetKey, dict[str, str]] = {}

    for record in records:
        target = _target_from_record(record)
        session_name = target['session'].strip()
        key = _target_key(target)
        if not session_name or key in selected_targets:
            continue
        selected_targets[key] = target
        targets_by_session.setdefault(session_name, []).append(target)

    matched_keys: set[TargetKey] = set()
    metadata_rows_changed = 0
    files_changed: list[str] = []

    for session_name, targets in targets_by_session.items():
        session_dir = resolve_session_dir(records_root, session_name)
        for filename in ('labels.jsonl', 'records.jsonl'):
            changed_rows, file_matches = _update_jsonl_file_batch(
                session_dir / filename,
                targets,
                steering=steering,
                throttle=throttle,
                update_steering=update_steering,
                update_throttle=update_throttle,
            )
            if changed_rows:
                files_changed.append(f'{session_name}/{filename}')
            metadata_rows_changed += changed_rows
            matched_keys.update(file_matches)

    failed_messages = [
        f"Could not find frame '{_target_label(target)}' in session '{target.get('session', '')}'."
        for key, target in selected_targets.items()
        if key not in matched_keys
    ]

    changed_fields = []
    if update_steering:
        changed_fields.append('steering')
    if update_throttle:
        changed_fields.append('speed')
    field_label = '/'.join(changed_fields) if changed_fields else 'controls'

    return {
        'selected_count': len(selected_targets),
        'updated_count': len(matched_keys),
        'metadata_rows_changed': metadata_rows_changed,
        'files_changed': files_changed,
        'failed_messages': failed_messages,
        'field_label': field_label,
        'matched_keys': sorted(matched_keys),
    }
