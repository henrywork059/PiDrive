# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller one-folder build spec for PiDrive piTrainer.

Build from the piTrainer component root:

    python -m PyInstaller --clean --noconfirm PACKAGING\piTrainer_onedir.spec

This intentionally uses a one-folder build rather than --onefile. It starts
faster, avoids temporary extraction, and keeps the launcher EXE small while the
large TensorFlow/PySide runtime libraries stay beside it in the app folder.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


ROOT = Path(SPECPATH).parent.parent.resolve()  # type: ignore[name-defined]
CONSOLE = os.environ.get("PITRAINER_CONSOLE", "0") == "1"


def safe_collect_data(package: str):
    try:
        return collect_data_files(package, include_py_files=False)
    except Exception:
        return []


def safe_collect_submodules(package: str):
    try:
        return collect_submodules(package)
    except Exception:
        return []


def safe_copy_metadata(package: str):
    try:
        return copy_metadata(package)
    except Exception:
        return []


datas = []
version_gate = ROOT / "config" / "version_gate.json"
if version_gate.exists():
    datas.append((str(version_gate), "config"))

# Keep plotting styles/fonts reliable without collecting unrelated dev files.
datas += safe_collect_data("matplotlib")

# Some wheels need distribution metadata at runtime.
for package_name in ("PySide6", "matplotlib", "numpy", "pandas", "Pillow", "tensorflow", "keras"):
    datas += safe_copy_metadata(package_name)

hiddenimports = [
    "matplotlib.backends.backend_qtagg",
    "PySide6.QtSvg",
    "PySide6.QtPrintSupport",
]
hiddenimports += safe_collect_submodules("matplotlib.backends")

# These are not used by piTrainer and are common causes of extra size.
excludes = [
    "tkinter",
    "tcl",
    "tk",
    "unittest",
    "doctest",
    "pdb",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "sphinx",
    "seaborn",
    "torch",
    "torchvision",
    "torchaudio",
    "cv2",
    "sklearn",
    "scipy.tests",
    "numpy.tests",
    "pandas.tests",
    "matplotlib.tests",
    "tensorflow.examples",
    "tensorflow_estimator",
]

analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PiTrainer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PiTrainer",
)
