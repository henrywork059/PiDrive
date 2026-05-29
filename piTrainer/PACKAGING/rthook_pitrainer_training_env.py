"""PyInstaller runtime environment defaults for piTrainer.

This runs before the frozen app imports TensorFlow/Keras. It keeps Keras on the
TensorFlow backend and avoids optional backend probing causing training-time
failures in the packaged EXE.
"""

from __future__ import annotations

import os

os.environ.setdefault("KERAS_BACKEND", "tensorflow")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("MPLBACKEND", "QtAgg")
