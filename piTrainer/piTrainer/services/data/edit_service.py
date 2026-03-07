from __future__ import annotations

import json
from pathlib import Path

from .record_loader_service import STEER_KEYS, THROTTLE_KEYS


def _line_matches(record: dict, frame_id: str, image_name: str, ts: str) -> bool:
    record_frame_id = str(record.get('frame_id', record.get('id', '')))
    record_ts = str(record.get('ts', record.get('timestamp', '')))
    record_image = str(
        record.get('image')
        or record.get('img')
        or record.get('filepath')
        or record.get('file')
        or record.get('filename')
        or record.get('path')
        or ''
    )
    record_image_name = Path(record_image).name
    return (
        record_frame_id == str(frame_id)
        and record_image_name == str(image_name)
        and record_ts == str(ts)
    )


def _first_existing_key(record: dict, keys: list[str], fallback: str) -> str:
    for key in keys:
        if key in record:
            return key
    return fallback


def _with_newline(raw_line: str) -> str:
    return raw_line if raw_line.endswith('\n') else raw_line + '\n'


def update_frame_controls(
    records_root: Path,
    session_name: str,
    frame_id: str,
    image_path: str,
    ts: str,
    steering: float,
    throttle: float,
) -> tuple[bool, str]:
    session_dir = records_root / session_name
    jsonl_path = session_dir / 'records.jsonl'
    if not jsonl_path.exists():
        return False, f"records.jsonl not found for session '{session_name}'."

    image_name = Path(image_path).name
    updated = False
    output_lines: list[str] = []

    with jsonl_path.open('r', encoding='utf-8') as handle:
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

            if not updated and _line_matches(record, frame_id=frame_id, image_name=image_name, ts=ts):
                steer_key = _first_existing_key(record, STEER_KEYS, 'steering')
                throttle_key = _first_existing_key(record, THROTTLE_KEYS, 'throttle')
                record[steer_key] = float(steering)
                record[throttle_key] = float(throttle)
                updated = True
                output_lines.append(json.dumps(record, ensure_ascii=False) + '\n')
                continue

            output_lines.append(_with_newline(raw_line))

    if not updated:
        return False, f"Could not find frame '{frame_id}' in session '{session_name}'."

    with jsonl_path.open('w', encoding='utf-8') as handle:
        handle.writelines(output_lines)

    return True, f"Updated steering/speed for frame '{frame_id}' in session '{session_name}'."
