# PATCH_NOTES_piCar_0_1_1.md

## Summary

This patch takes the stable recording build `piCar_0_1_0` and makes the
first small step toward a more modular, "single-responsibility" layout.

### Behaviour

- **Recording, control, motors, and UI behaviour are unchanged** compared
  to `piCar_0_1_0`. The same files are written, with the same structure
  and contents.
- This is a **refactor-only** patch intended to make future changes safer
  and easier to debug.

## Code structure changes

### New module: `recorder_step.py`

- Added a new file whose only job is to perform **one recording tick**:

  ```python
  from data_recorder import DataRecorder

  def record_step(recorder: DataRecorder, camera, control_state):
      recorder.maybe_record(camera, control_state)
  ```

- This isolates the per-frame recording logic into a single function so
  that other parts of the code do not need to know *how* a frame is
  written, only *that* it is recorded.

### Updated: `control_api.py`

- Previously, `handle_control_post` called the recorder directly:

  ```python
  recorder.maybe_record(camera, control_state)
  ```

- It now calls the new wrapper instead:

  ```python
  from recorder_step import record_step
  ...
  record_step(recorder, camera, control_state)
  ```

- This keeps `control_api.py` focused on:
  - maintaining the current control state
  - updating the motor output
  - delegating to the recorder and status functions

## Rationale

- By moving the "record exactly one frame" action into its own module,
  we get closer to the goal of **one clear responsibility per file**.
- Future patches can evolve `recorder_step.py` (e.g. different formats,
  error handling, extra metadata) without touching `control_api.py`.
- If recording ever misbehaves, you only need to inspect:
  - `recorder_step.py`
  - `data_recorder.py`
  and the rest of the system can remain untouched.
