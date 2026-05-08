# PiSD Test Plan

## Current placeholder checks

From inside `PiSD/`:

```bash
python PiSD.py --status-only
python -m py_compile PiSD.py
```

After installing packages:

```bash
python -m pip install -r requirement.txt
python PiSD.py
```

Open:

```text
http://127.0.0.1:5050
http://127.0.0.1:5050/api/status
```

## Future smoke tests

### GUI smoke test

- page loads
- no console errors
- status panel updates
- unavailable features are clearly labelled

### API smoke test

- `/api/status` returns JSON
- settings GET/POST round-trips safely
- invalid settings return readable errors
- stop endpoint always responds

### Camera simulation test

- simulated preview starts
- simulated frame changes over time
- snapshot saves a new image each time
- no repeated stale frame bug

### Motor simulation test

- steering command updates state
- throttle command updates state
- stop command resets output
- limits are clamped safely

### Hardware adapter test

Only run on Raspberry Pi after simulation behavior is stable.

- camera detected
- preview starts
- snapshot saves current frame
- motor adapter initializes
- stop command works
- settings survive restart

## Verification rule

Patch notes must only claim tests that were actually run.
