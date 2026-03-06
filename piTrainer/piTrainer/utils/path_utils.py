from __future__ import annotations

from pathlib import Path
import re



def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path



def safe_filename(name: str, default: str = "model") -> str:
    value = (name or "").strip() or default
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value[:120]
