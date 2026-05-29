from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
import os
import sys
import tempfile
import warnings


@dataclass
class CapturedTensorFlowOutput:
    """Captured noisy TensorFlow/TFLite console output from a short operation."""

    stdout: str = ""
    stderr: str = ""
    warnings: list[str] = field(default_factory=list)


_LITERT_WARNING_TEXT = "Please use the LiteRT interpreter from the ai_edge_litert package"


def configure_tensorflow_quiet_env() -> None:
    """Set safe TensorFlow log defaults before TensorFlow is imported."""

    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


def _flush_standard_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass


@contextmanager
def quiet_tensorflow_output() -> CapturedTensorFlowOutput:
    """Capture TensorFlow/TFLite Python, absl, and native C++ console noise.

    TensorFlow Lite conversion and interpreter creation can write directly to the
    process stdout/stderr file descriptors before Python logging has a chance to
    filter the messages. A normal ``redirect_stderr`` only catches Python-level
    writes, so this helper also redirects the OS-level stdout/stderr descriptors
    to a temporary file during the small export/validation operation.

    The captured text is returned to the caller for optional short summaries, but
    it is not printed to the user's terminal during normal successful runs.
    """

    captured = CapturedTensorFlowOutput()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    native_buffer = None
    saved_fds: dict[int, int] = {}
    old_tf_level = os.environ.get("TF_CPP_MIN_LOG_LEVEL")
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    try:
        native_buffer = tempfile.TemporaryFile(mode="w+b")
        _flush_standard_streams()
        for fd_no in (1, 2):
            try:
                saved_fds[fd_no] = os.dup(fd_no)
                os.dup2(native_buffer.fileno(), fd_no)
            except Exception:
                saved_fd = saved_fds.pop(fd_no, None)
                if saved_fd is not None:
                    try:
                        os.close(saved_fd)
                    except Exception:
                        pass
    except Exception:
        native_buffer = None
        for fd_no, saved_fd in list(saved_fds.items()):
            try:
                os.dup2(saved_fd, fd_no)
            except Exception:
                pass
            try:
                os.close(saved_fd)
            except Exception:
                pass
            saved_fds.pop(fd_no, None)

    try:
        with warnings.catch_warnings(record=True) as warning_records:
            warnings.simplefilter("always")
            warnings.filterwarnings(
                "ignore",
                message=f".*{_LITERT_WARNING_TEXT}.*",
                category=UserWarning,
            )
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                yield captured
            captured.warnings = [str(item.message) for item in warning_records]
    finally:
        _flush_standard_streams()
        native_text = ""
        if native_buffer is not None:
            try:
                native_buffer.flush()
            except Exception:
                pass

        for fd_no, saved_fd in list(saved_fds.items()):
            try:
                os.dup2(saved_fd, fd_no)
            except Exception:
                pass
            try:
                os.close(saved_fd)
            except Exception:
                pass
            saved_fds.pop(fd_no, None)

        if native_buffer is not None:
            try:
                native_buffer.seek(0)
                native_text = native_buffer.read().decode("utf-8", errors="replace").strip()
            except Exception:
                native_text = ""
            try:
                native_buffer.close()
            except Exception:
                pass

        captured.stdout = stdout_buffer.getvalue().strip()
        captured.stderr = "\n".join(
            part for part in (stderr_buffer.getvalue().strip(), native_text) if part
        )
        if old_tf_level is None:
            os.environ.pop("TF_CPP_MIN_LOG_LEVEL", None)
        else:
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = old_tf_level
