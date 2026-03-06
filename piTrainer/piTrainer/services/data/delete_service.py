from __future__ import annotations

import json
from pathlib import Path


def _line_matches(record: dict, frame_id: str, image_name: str, ts: str) -> bool:
    record_frame_id = str(record.get("frame_id", record.get("id", "")))
    record_ts = str(record.get("ts", record.get("timestamp", "")))
    record_image = str(
        record.get("image")
        or record.get("img")
        or record.get("filepath")
        or record.get("file")
        or record.get("filename")
        or record.get("path")
        or ""
    )
    record_image_name = Path(record_image).name
    return (
        record_frame_id == str(frame_id)
        and record_image_name == str(image_name)
        and record_ts == str(ts)
    )


def delete_frame_from_session(records_root: Path, session_name: str, frame_id: str, image_path: str, ts: str = "") -> tuple[bool, str]:
    session_dir = records_root / session_name
    jsonl_path = session_dir / "records.jsonl"
    if not jsonl_path.exists():
        return False, f"records.jsonl not found for session '{session_name}'."

    image_name = Path(image_path).name
    kept_lines: list[str] = []
    deleted = False

    with jsonl_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                kept_lines.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
                continue

            if not deleted and _line_matches(record, frame_id=frame_id, image_name=image_name, ts=ts):
                deleted = True
                continue
            kept_lines.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")

    if not deleted:
        return False, f"Could not find frame '{frame_id}' in session '{session_name}'."

    with jsonl_path.open("w", encoding="utf-8") as handle:
        handle.writelines(kept_lines)

    if image_path:
        try:
            image_file = Path(image_path)
            if image_file.exists():
                image_file.unlink()
        except OSError as exc:
            return True, f"Frame metadata deleted, but image file could not be removed: {exc}"

    return True, f"Deleted frame '{frame_id}' from session '{session_name}'."
