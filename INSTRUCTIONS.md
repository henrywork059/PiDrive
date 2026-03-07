# PiDrive Maintenance Instructions

This document provides safe maintenance guidance for contributors who need to review or clean up the repository **without changing function behavior**.

## Scope of safe cleanup

Allowed cleanup examples:

- Improve documentation (`README`, comments, architecture notes).
- Rename unclear variables only when semantics remain identical.
- Reformat code (whitespace/import order) without modifying logic.
- Remove dead comments or duplicate notes.
- Clarify error messages where no control flow changes occur.

Avoid during no-behavior-change tasks:

- Changing function signatures.
- Altering branching logic, return values, or side effects.
- Modifying API contracts (request/response formats, route names).
- Tuning model or control behavior.

## Review checklist

Use this checklist during code review and cleanup passes:

1. **Entry points**
   - `piCar_0_3_2/server.py`
   - `piTrainer/main.py`
2. **Core runtime flow**
   - Camera init and frame stream (`camera.py`, `video_stream.py`)
   - Control handling and state (`control_api.py`, `control_state.py`)
   - Recording and session management (`data_recorder.py`)
   - Model load/inference path (`model_manager.py`, `autopilot.py`)
3. **Trainer architecture**
   - UI layout and page composition (`piTrainer/piTrainer/pages/`)
   - Page panel components (`piTrainer/piTrainer/panels/`)
   - Business logic services (`piTrainer/piTrainer/services/`)
   - App-wide state (`piTrainer/piTrainer/app_state.py`)
4. **Consistency checks**
   - Naming consistency across files and classes
   - Inline docs for non-obvious behavior
   - Error-path messages clear and actionable

## Documentation standards

When updating docs:

- Keep setup commands copy-paste friendly.
- Include both Windows and macOS/Linux activation examples where relevant.
- Prefer short, task-oriented sections (Run, Configure, Troubleshoot).
- Reference exact paths and filenames for key components.

## Suggested contributor workflow

1. Read root `README.md` and `piTrainer/README.md`.
2. Identify ambiguity or drift between code and docs.
3. Apply non-functional cleanup.
4. Verify no function signatures or behavior changed.
5. Summarize the cleanup in commit message with “non-functional” wording.

## Commit message guideline

Use commit titles similar to:

- `docs: expand root README with project structure and quick start`
- `chore: add maintenance instructions for no-behavior-change cleanups`

This helps reviewers quickly identify safe, documentation-focused updates.
