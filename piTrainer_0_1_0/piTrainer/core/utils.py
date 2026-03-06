from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import os
import re

def expand_path(p: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(p))).resolve()

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def safe_filename(name: str, default: str = "model") -> str:
    name = name.strip() or default
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name[:120]
