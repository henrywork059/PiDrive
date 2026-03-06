from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

STEER_KEYS = ["steering", "angle", "user/angle", "user_angle", "target_steering"]
THR_KEYS   = ["throttle", "user/throttle", "user_throttle", "target_throttle"]
IMG_KEYS   = ["image", "img", "filepath", "file", "filename", "path"]
MODE_KEYS  = ["mode", "drive_mode"]

def list_sessions(records_root: Path) -> list[str]:
    if not records_root.exists():
        return []
    sessions = []
    for p in sorted(records_root.iterdir()):
        if not p.is_dir():
            continue
        if (p / "records.jsonl").exists() and (p / "images").exists():
            sessions.append(p.name)
    return sessions

def _coalesce(d: dict, keys: list[str], default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def load_records_jsonl(records_root: Path, sessions: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for sess in sessions:
        sess_dir = records_root / sess
        jsonl = sess_dir / "records.jsonl"
        if not jsonl.exists():
            continue
        with jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                img_rel = _coalesce(rec, IMG_KEYS, None)
                if isinstance(img_rel, str):
                    img_path = (sess_dir / img_rel).resolve()
                else:
                    img_path = None

                row = {
                    "session": sess,
                    "frame_id": rec.get("frame_id", rec.get("id", "")),
                    "ts": rec.get("ts", rec.get("timestamp", "")),
                    "mode": _coalesce(rec, MODE_KEYS, ""),
                    "steering": _coalesce(rec, STEER_KEYS, 0.0),
                    "throttle": _coalesce(rec, THR_KEYS, 0.0),
                    "abs_image": str(img_path) if img_path else "",
                }

                # keep some optional metadata if present
                for k in ["cam_w", "cam_h", "format", "camera_w", "camera_h"]:
                    if k in rec:
                        row[k] = rec.get(k)

                rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Normalize numeric
    df["steering"] = pd.to_numeric(df["steering"], errors="coerce").fillna(0.0).astype("float32")
    df["throttle"] = pd.to_numeric(df["throttle"], errors="coerce").fillna(0.0).astype("float32")

    # Drop missing image path
    df["abs_image"] = df["abs_image"].astype(str)
    df = df[df["abs_image"].str.len() > 0].copy()

    # Drop non-existing files
    df = df[df["abs_image"].apply(lambda p: Path(p).exists())].copy()

    return df.reset_index(drop=True)

def basic_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    return {
        "n": int(len(df)),
        "sessions": int(df["session"].nunique()) if "session" in df.columns else 0,
        "steering_mean": float(df["steering"].mean()),
        "steering_std": float(df["steering"].std()),
        "throttle_mean": float(df["throttle"].mean()),
        "throttle_std": float(df["throttle"].std()),
    }
