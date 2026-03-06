from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

STEER_KEYS = ["steering", "angle", "user/angle", "user_angle", "target_steering"]
THROTTLE_KEYS = ["throttle", "user/throttle", "user_throttle", "target_throttle"]
IMAGE_KEYS = ["image", "img", "filepath", "file", "filename", "path"]
MODE_KEYS = ["mode", "drive_mode"]



def coalesce_value(record: dict, keys: list[str], default=None):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return default



def build_row(session_name: str, session_dir: Path, record: dict) -> dict:
    image_rel = coalesce_value(record, IMAGE_KEYS, "")
    image_path = (session_dir / str(image_rel)).resolve() if image_rel else None
    row = {
        "session": session_name,
        "frame_id": record.get("frame_id", record.get("id", "")),
        "ts": record.get("ts", record.get("timestamp", "")),
        "mode": coalesce_value(record, MODE_KEYS, ""),
        "steering": coalesce_value(record, STEER_KEYS, 0.0),
        "throttle": coalesce_value(record, THROTTLE_KEYS, 0.0),
        "abs_image": str(image_path) if image_path else "",
    }
    for key in ["cam_w", "cam_h", "format", "camera_w", "camera_h"]:
        if key in record:
            row[key] = record.get(key)
    return row



def load_records_dataframe(records_root: Path, sessions: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for session_name in sessions:
        session_dir = records_root / session_name
        jsonl_path = session_dir / "records.jsonl"
        if not jsonl_path.exists():
            continue
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rows.append(build_row(session_name, session_dir, record))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["steering"] = pd.to_numeric(df["steering"], errors="coerce").fillna(0.0).astype("float32")
    df["throttle"] = pd.to_numeric(df["throttle"], errors="coerce").fillna(0.0).astype("float32")
    df["abs_image"] = df["abs_image"].astype(str)
    return df.reset_index(drop=True)



def build_filtered_dataframe(df: pd.DataFrame, only_manual: bool) -> pd.DataFrame:
    if df.empty:
        return df
    filtered = df[df["abs_image"].astype(str).str.len() > 0].copy()
    filtered = filtered[filtered["abs_image"].apply(lambda path: Path(path).exists())].copy()
    if only_manual and "mode" in filtered.columns:
        manual_mask = filtered["mode"].astype(str).str.lower().isin({"manual", "user", "train"})
        if manual_mask.any():
            filtered = filtered[manual_mask].copy()
    return filtered.reset_index(drop=True)
