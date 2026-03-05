# PATCH_NOTES_piCar_0_1_2.md

## Summary

This patch builds on the stable, recording-safe version `piCar_0_1_1`
and makes a small structural improvement to how the control state is
defined, without changing behaviour.

- **Runtime behaviour is unchanged** compared to `piCar_0_1_1`.
- Recording, motors, UI, and APIs work exactly as before.
- The goal is to make future changes to the control state safer and
  easier to manage.

## Changes

### New module: `control_state.py`

- Introduces a documented representation of the control state:

  ```python
  @dataclass
  class ControlState:
      steering: float = 0.0
      throttle: float = 0.0
      mode: str = "manual"
      last_update: float = 0.0
  ```

- Provides a single helper to construct the initial state dict:

  ```python
  def make_initial_state() -> Dict[str, Any]:
      return {
          "steering": 0.0,
          "throttle": 0.0,
          "mode": "manual",
          "last_update": time.time(),
      }
  ```

- The rest of the system still uses a plain `dict` for compatibility,
  but the expected fields and their types are now documented in one
  place.

### Updated: `control_api.py`

- Previously the initial control state was created inline as a dict
  literal:

  ```python
  control_state = {
      "steering": 0.0,
      "throttle": 0.0,
      "mode": "manual",
      "last_update": time.time(),
  }
  control_lock = threading.Lock()
  ```

- It now delegates to `make_initial_state()`:

  ```python
  from control_state import make_initial_state

  control_state = make_initial_state()
  control_lock = threading.Lock()
  ```

- All later reads and writes still operate on the same `control_state`
  dict, so the behaviour of `/api/control`, `/api/status`, the motors,
  and the recorder is unchanged.

## Rationale

- Centralising the construction of the control state makes it easier to
  add new fields (e.g. `auto_steer`, `lap_id`, etc.) in future patches
  without missing a place where the defaults should be set.
- If any future bug involves the control state keys or defaults, it is
  now obvious that `control_state.py` is the first file to inspect.
