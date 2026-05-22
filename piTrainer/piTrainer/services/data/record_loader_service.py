from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .session_service import resolve_session_dir
from .visibility_service import is_record_hidden

STEER_KEYS = ["steering", "angle", "user/angle", "user_angle", "target_steering"]
THROTTLE_KEYS = ["throttle", "user/throttle", "user_throttle", "target_throttle"]
IMAGE_KEYS = ["frame", "image", "img", "filepath", "file", "filename", "path", "relative_file"]
MODE_KEYS = ["mode", "drive_mode", "session_label", "label"]


def coalesce_value(record: dict, keys: list[str], default=None):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return default


def _project_root_from_session(session_dir: Path) -> Path:
    """Return the likely PiSD project root for a session under recordings/."""
    resolved = Path(session_dir).expanduser().resolve()
    parts = resolved.parts
    if "recordings" in parts:
        idx = parts.index("recordings")
        if idx > 0:
            return Path(*parts[:idx])
    return resolved.parent


def _first_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except Exception:
            resolved = candidate
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _resolve_image_path(session_dir: Path, record: dict) -> Path | None:
    """Resolve PiSD and legacy image path fields to an existing image when possible.

    Fast path is intentionally optimized for PiSD labels.jsonl:
    `session_dir / row["frame"]`. This keeps loading responsive for large
    sessions and still works when a session folder is copied to a PC.
    """
    session_dir = Path(session_dir).expanduser().resolve()

    frame_rel = record.get("frame")
    if frame_rel:
        frame_path = session_dir / str(frame_rel)
        if frame_path.is_file():
            return frame_path.resolve()

    project_root: Path | None = None

    relative_file = record.get("relative_file")
    if relative_file:
        relative_text = str(relative_file)
        relative_path = Path(relative_text)
        if relative_path.is_absolute():
            if relative_path.is_file():
                return relative_path.resolve()
        else:
            project_root = _project_root_from_session(session_dir)
            candidate = project_root / relative_text
            if candidate.is_file():
                return candidate.resolve()
            # If the user selected PiSD/recordings as root, this fallback can still help.
            fallback = session_dir.parent.parent / relative_text
            if fallback.is_file():
                return fallback.resolve()

    image_rel = coalesce_value(record, ["image", "img", "filepath", "file", "filename", "path"], "")
    if image_rel:
        image_text = str(image_rel)
        image_path = Path(image_text)
        if image_path.is_absolute():
            if image_path.is_file():
                return image_path.resolve()
        else:
            candidate = session_dir / image_text
            if candidate.is_file():
                return candidate.resolve()
            if project_root is None:
                project_root = _project_root_from_session(session_dir)
            candidate = project_root / image_text
            if candidate.is_file():
                return candidate.resolve()

    return None


def _training_label_record(record: dict[str, Any]) -> dict[str, Any]:
    training_label = record.get("training_label")
    if isinstance(training_label, dict):
        merged = dict(record)
        merged.update({k: v for k, v in training_label.items() if v is not None})
        return merged
    return record


def _json_safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
            return dict(decoded) if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _load_manifest_defaults(session_dir: Path) -> dict[str, Any]:
    manifest_path = Path(session_dir) / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except Exception:
        return {}
    if not isinstance(manifest, dict):
        return {}
    return {
        "overlay_settings": _json_safe_mapping(manifest.get("overlay_settings")),
        "overlay_schema_version": manifest.get("overlay_schema_version", ""),
        "overlay_settings_source": manifest.get("overlay_settings_source", "manifest"),
        "session_label": str(manifest.get("label") or manifest.get("session_label") or ""),
        "manifest_session_id": str(manifest.get("session_id") or ""),
    }


def _overlay_metadata(record: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    settings = _json_safe_mapping(record.get("overlay_settings")) or _json_safe_mapping(defaults.get("overlay_settings"))
    schema = record.get("overlay_schema_version", defaults.get("overlay_schema_version", ""))
    source = record.get("overlay_settings_source", defaults.get("overlay_settings_source", ""))
    return {
        "overlay_settings": settings,
        "overlay_schema_version": str(schema or ""),
        "overlay_settings_source": str(source or ""),
        "has_overlay_settings": bool(settings),
    }


def build_row(
    session_name: str,
    session_dir: Path,
    record: dict,
    *,
    source: str = "records.jsonl",
    manifest_defaults: dict[str, Any] | None = None,
) -> dict:
    record = _training_label_record(record)
    image_path = _resolve_image_path(session_dir, record)
    steering = coalesce_value(record, STEER_KEYS, 0.0)
    throttle = coalesce_value(record, THROTTLE_KEYS, 0.0)
    overlay_meta = _overlay_metadata(record, manifest_defaults)
    inferred_mode = coalesce_value(record, MODE_KEYS, "")
    if not inferred_mode and manifest_defaults:
        inferred_mode = manifest_defaults.get("session_label") or manifest_defaults.get("manifest_session_id") or session_name
    if not inferred_mode:
        inferred_mode = session_name
    row = {
        "session": session_name,
        "session_dir": str(Path(session_dir).resolve()),
        "source": source,
        "frame_id": record.get("frame_id", record.get("id", record.get("source_frame_seq", ""))),
        "frame_index": record.get("frame_index", record.get("source_frame_seq", "")),
        "ts": record.get("ts", record.get("timestamp", record.get("timestamp_utc", record.get("saved_at_utc", "")))),
        "mode": inferred_mode,
        "steering": steering,
        "throttle": throttle,
        "abs_image": str(image_path) if image_path else "",
        "frame": record.get("frame", ""),
        "relative_file": record.get("relative_file", ""),
        "source_frame_seq": record.get("source_frame_seq", ""),
        **overlay_meta,
    }
    for key in ["cam_w", "cam_h", "format", "camera_w", "camera_h", "source_frame_bytes"]:
        if key in record:
            row[key] = record.get(key)
    return row


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError:
                continue




def _record_identity_key(record: dict[str, Any]) -> tuple[str, str, str]:
    merged = _training_label_record(record)
    frame_id = str(merged.get("frame_id", merged.get("id", merged.get("source_frame_seq", ""))) or "")
    ts = str(merged.get("ts", merged.get("timestamp", merged.get("timestamp_utc", merged.get("saved_at_utc", "")))) or "")
    image_name = Path(str(coalesce_value(merged, IMAGE_KEYS, "") or "")).name
    return frame_id, ts, image_name


def _hidden_record_identities(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    identities: set[tuple[str, str, str]] = set()
    for _line_no, record in _iter_jsonl(path):
        if isinstance(record, dict) and is_record_hidden(record):
            identities.add(_record_identity_key(record))
    return identities

def _load_labels_rows(session_name: str, session_dir: Path) -> list[dict]:
    labels_path = session_dir / "labels.jsonl"
    if not labels_path.exists():
        return []
    manifest_defaults = _load_manifest_defaults(session_dir)
    rows = [
        build_row(session_name, session_dir, record, source="labels.jsonl", manifest_defaults=manifest_defaults)
        for _line_no, record in _iter_jsonl(labels_path)
        if isinstance(record, dict) and not is_record_hidden(record)
    ]
    # labels.jsonl is the primary PiSD training file, but keep only usable image rows.
    usable = [row for row in rows if str(row.get("abs_image", ""))]
    return usable


def _load_records_rows(
    session_name: str,
    session_dir: Path,
    hidden_label_identities: set[tuple[str, str, str]] | None = None,
) -> list[dict]:
    records_path = session_dir / "records.jsonl"
    if not records_path.exists():
        return []
    hidden_label_identities = hidden_label_identities or set()
    manifest_defaults = _load_manifest_defaults(session_dir)
    rows = [
        build_row(session_name, session_dir, record, source="records.jsonl", manifest_defaults=manifest_defaults)
        for _line_no, record in _iter_jsonl(records_path)
        if isinstance(record, dict)
        and not is_record_hidden(record)
        and _record_identity_key(record) not in hidden_label_identities
    ]
    return rows


def load_records_dataframe(records_root: Path, sessions: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for session_name in sessions:
        session_dir = resolve_session_dir(records_root, session_name)

        # Latest PiSD loading priority:
        # 1) labels.jsonl (primary training labels)
        # 2) records.jsonl training_label / direct debug fields (fallback)
        label_rows = _load_labels_rows(session_name, session_dir)
        if label_rows:
            rows.extend(label_rows)
            continue
        hidden_label_identities = _hidden_record_identities(session_dir / "labels.jsonl")
        rows.extend(_load_records_rows(session_name, session_dir, hidden_label_identities=hidden_label_identities))

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["steering"] = pd.to_numeric(df["steering"], errors="coerce").fillna(0.0).clip(-1.0, 1.0).astype("float32")
    df["throttle"] = pd.to_numeric(df["throttle"], errors="coerce").fillna(0.0).clip(-1.0, 1.0).astype("float32")
    df["abs_image"] = df["abs_image"].astype(str)
    if "overlay_settings" not in df.columns:
        df["overlay_settings"] = [{} for _ in range(len(df))]
    if "overlay_schema_version" not in df.columns:
        df["overlay_schema_version"] = ""
    if "overlay_settings_source" not in df.columns:
        df["overlay_settings_source"] = ""
    if "has_overlay_settings" not in df.columns:
        df["has_overlay_settings"] = df["overlay_settings"].map(bool)
    return df.reset_index(drop=True)


def build_filtered_dataframe(df: pd.DataFrame, only_manual: bool) -> pd.DataFrame:
    if df.empty:
        return df
    filtered = df[df["abs_image"].astype(str).str.len() > 0].copy()
    filtered = filtered[filtered["abs_image"].map(os.path.isfile)].copy()
    if only_manual and "mode" in filtered.columns:
        mode_values = filtered["mode"].astype(str).str.lower()
        manual_mask = mode_values.isin({"manual", "user", "train", "manual_drive"}) | mode_values.str.contains("manual", na=False)
        if manual_mask.any():
            filtered = filtered[manual_mask].copy()
    return filtered.reset_index(drop=True)
