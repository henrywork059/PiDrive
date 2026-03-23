from __future__ import annotations

import sys
from pathlib import Path

CUSTOMDRIVE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CUSTOMDRIVE_ROOT.parents[0]
PISERVER_ROOT = REPO_ROOT / 'PiServer'
CONFIG_DIR = CUSTOMDRIVE_ROOT / 'config'
DATA_DIR = CUSTOMDRIVE_ROOT / 'data'
PISERVER_RUNTIME_PATH = PISERVER_ROOT / 'config' / 'runtime.json'


def ensure_piserver_import_paths() -> None:
    for path in (REPO_ROOT, PISERVER_ROOT):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
