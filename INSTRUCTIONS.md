# PiDrive Maintenance Instructions

This document provides safe maintenance guidance for contributors who need to review or clean up the repository **without changing runtime behavior**.

## Scope of safe cleanup

Allowed examples:

- Update documentation to match the current source tree and entry points.
- Rename unclear local variables when behavior is unchanged.
- Reformat code (whitespace/import order) without changing logic.
- Remove stale comments and dead documentation references.
- Improve wording of user-facing errors where control flow is unchanged.

Avoid during non-functional cleanup tasks:

- Changing route names, API contracts, or payload structures.
- Altering mission/training/control logic.
- Changing model defaults that affect output behavior.
- Modifying side effects (file writes, motor output, recorder behavior).

## Current project entry points

- `piCar_0_3_2/server.py`
- `PiServer/server.py`
- `piTrainer/main.py`
- `CustomTrainer/run_custom_trainer.py`
- `CustomDrive/run_custom_drive_demo.py`

## Review checklist

1. **Runtime stacks**
   - Legacy runtime (`piCar_0_3_2/*`)
   - Modular runtime (`PiServer/piserver/*`)
2. **Desktop trainers**
   - Steering/throttle trainer (`piTrainer/piTrainer/*`)
   - YOLO trainer (`CustomTrainer/custom_trainer/*`)
3. **Mission scaffold**
   - State machine + controller (`CustomDrive/custom_drive/*`)
4. **Cross-project consistency**
   - README and quick-start commands match real files.
   - Mentioned modules/paths exist.
   - Patch notes remain historical (do not rewrite release history unless asked).

## Documentation standards

When updating docs:

- Keep commands copy/paste friendly.
- Include Windows + macOS/Linux virtualenv activation examples when relevant.
- Use concise task-oriented sections (`Install`, `Run`, `Notes`).
- Prefer concrete file paths over vague references.

## Suggested contributor workflow

1. Check `README.md` and each project-level `README.md`.
2. Confirm entry points and folder names from source files.
3. Update docs to remove stale version-specific phrasing unless still accurate.
4. Run lightweight checks (`python -m compileall` or project-specific smoke checks) when possible.
5. Commit with a `docs:` or `chore:` prefix.
