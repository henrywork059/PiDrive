from __future__ import annotations

import os

# Keep TensorFlow's C++ INFO messages out of normal UI/startup logs when
# TensorFlow is imported later by training, validation, or export code.
# This is set before importing piTrainer.app when users run `python main.py`.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

__all__ = [
    "app",
    "app_state",
    "main_window",
]
