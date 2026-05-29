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


ROOT = Path(SPECPATH).parent.resolve()  # type: ignore[name-defined]
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
    # Required indirectly by pyparsing.testing, which matplotlib imports during startup.
    # Do not exclude it or the frozen EXE fails before the main window opens.
    "unittest",
    "unittest.case",
    "unittest.loader",
    "unittest.mock",
    "unittest.result",
    "unittest.runner",
    "unittest.suite",
    "unittest.util",
    # TensorFlow/Keras modules used by the Train page are imported dynamically.
    # Keep these explicit so the frozen app can open and still train, not only view data.
    "tensorflow",
    "tensorflow.keras",
    "tensorflow.keras.callbacks",
    "tensorflow.keras.layers",
    "tensorflow.keras.losses",
    "tensorflow.keras.models",
    "tensorflow.keras.optimizers",
    "tensorflow.keras.utils",
    "tensorflow.lite",
    "tensorflow.lite.python.interpreter",
    "keras",
    "keras.src",
    "keras.src.backend",
    "keras.src.backend.tensorflow",
    "keras.src.backend.tensorflow.core",
    "keras.src.backend.tensorflow.trainer",
    "keras.src.callbacks",
    "keras.src.layers",
    "keras.src.losses",
    "keras.src.models",
    "keras.src.ops",
    "keras.src.optimizers",
    "keras.src.saving",
    "keras.src.utils",
]
hiddenimports += safe_collect_submodules("matplotlib.backends")
hiddenimports += safe_collect_submodules("keras.src.backend.tensorflow")
hiddenimports += safe_collect_submodules("keras.src.callbacks")
hiddenimports += safe_collect_submodules("keras.src.layers")
hiddenimports += safe_collect_submodules("keras.src.losses")
hiddenimports += safe_collect_submodules("keras.src.models")
hiddenimports += safe_collect_submodules("keras.src.optimizers")
hiddenimports += safe_collect_submodules("keras.src.saving")

# These are not used by piTrainer and are common causes of extra size.
excludes = [
    "tkinter",
    "tcl",
    "tk",
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
    "keras.src.backend.torch",
    "keras.src.backend.jax",
]

runtime_hooks = []
train_runtime_hook = ROOT / "PACKAGING" / "rthook_pitrainer_training_env.py"
if train_runtime_hook.exists():
    runtime_hooks.append(str(train_runtime_hook))

analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
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
