# recorder_step.py
"""Single-responsibility wrapper for one recording tick.

This keeps the per-frame recording logic in one place so that
`control_api.handle_control_post` only needs to call a single
function, and all details of how a frame is stored remain inside
the recorder modules.
"""

from typing import Mapping, Any

from data_recorder import DataRecorder


def record_step(recorder: DataRecorder, camera: Any, control_state: Mapping[str, Any]) -> None:
    """Record one frame if recording is enabled.

    This is a very thin wrapper around ``recorder.maybe_record`` to avoid
    duplicating logic in ``control_api.py``. Behaviour is unchanged: if the
    recorder is not currently recording, this is a no-op.
    """
    recorder.maybe_record(camera, control_state)
