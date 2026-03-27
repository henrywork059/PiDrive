# PiDrive Maintenance Instructions

This document explains how to make safe, maintainable updates across the PiDrive monorepo.

## Purpose

Use these instructions when you are doing **documentation improvements**, **non-functional cleanup**, or **lightweight maintenance** that should not change runtime behavior.

## Golden rule

If a change can affect robot motion, model output, API behavior, file formats, or deployment behavior, treat it as a functional change and handle it with extra review and testing.

## Safe cleanup scope

### Usually safe

- Update README and instruction files for clarity, accuracy, and onboarding.
- Improve naming of local variables where behavior is unchanged.
- Reformat code (whitespace, import ordering, comments) without logic edits.
- Remove stale comments and dead documentation references.
- Improve wording in user-facing text where control flow is unchanged.

### Usually not safe

- Changing API routes, request/response schema, or endpoint semantics.
- Changing algorithm selection rules or control-loop behavior.
- Changing default model paths, preprocessing parameters, or runtime tuning values.
- Changing recorder output format, field names, or folder structure.
- Changing motor output constraints, safety cutoffs, or camera initialization behavior.

## Current project entry points

Use these as the canonical startup scripts when checking docs:

- `piCar_0_3_2/server.py`
- `PiServer/server.py`
- `piTrainer/main.py`
- `CustomTrainer/run_custom_trainer.py`
- `CustomDrive/run_custom_drive_demo.py`

## Current code status map (important for maintenance)

### Active projects (current version)

- `PiServer/`
- `piTrainer/`
- `CustomTrainer/`
- `CustomDrive/`
- `piCar_0_3_2/` (legacy-compatible runtime, still intentionally shipped)

### Non-active / reference only

- `PiServer_0_3_4/`
- `PiServer_0_4_1/`
- repository-root timestamped `*.zip` snapshots

When updating docs, explicitly label these as archive/reference assets so readers do not mistake them for current deployment targets.

## Maintenance workflow (recommended)

1. **Read top-level docs first**
   - `README.md`
   - `INSTRUCTIONS.md`
2. **Verify paths and commands**
   - Confirm every documented path exists.
   - Confirm every run command points to a real entry script.
3. **Apply small focused edits**
   - Prefer multiple tiny commits over one broad undocumented rewrite.
4. **Run lightweight checks**
   - For docs-only changes: check Markdown formatting and link/path validity.
   - For mixed changes: run project-specific smoke checks.
5. **Write clear commit messages**
   - Use prefixes like `docs:` or `chore:`.
   - Mention the exact docs updated and why.

## Documentation standards

When editing docs:

- Use clear task-oriented sections (`Prerequisites`, `Install`, `Run`, `Troubleshooting`).
- Keep commands copy/paste ready.
- Include macOS/Linux + Windows virtualenv activation when relevant.
- Prefer explicit file paths instead of vague references.
- List assumptions (Python version, Pi-only dependencies, expected OS) near commands.
- Document fallback behavior (for missing camera/GPIO/TFLite) when applicable.

## Cross-project review checklist

### Runtime stacks

- `piCar_0_3_2/*` (legacy)
- `PiServer/piserver/*` (modular runtime)

### Desktop apps

- `piTrainer/piTrainer/*` (driving-model trainer)
- `CustomTrainer/custom_trainer/*` (YOLO workflow)

### Mission scaffold

- `CustomDrive/custom_drive/*`

### Consistency checks

- README quick-start commands still match real scripts.
- Mentioned config files still exist.
- Patch notes are treated as historical records unless specifically asked to revise.
- Archive/reference folders are clearly marked as non-active.
- Utility launchers are not presented as primary entry points unless they are part of the current production flow.

## Risk notes

If you touch files that interact with camera, motor, inference, or route logic:

- assume behavior can be safety-critical,
- avoid silent defaults changes,
- and require explicit testing notes in your commit/PR.

## Suggested validation commands

Run from repository root as needed:

```bash
# quick path sanity
rg --files | rg -i 'readme|instructions|main.py|server.py|run_'

# optional Python syntax smoke check (if dependencies are not required)
python -m compileall PiServer piTrainer CustomTrainer CustomDrive

# detect likely non-active files/folders to document explicitly
rg --files | rg '(^PiServer_0_|\\.zip$)'
```

## Commit and PR expectations

- Keep PR scope tight and explain intent in the first paragraph.
- Include a concise testing/check list with command outputs.
- If a check cannot run due to environment limits, call that out explicitly.
