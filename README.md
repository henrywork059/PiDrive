# PiDrive

PiDrive is a monorepo for Raspberry Pi car runtime, steering-model training. Historical network onboarding remains archived in the repository.

This document is synchronized to the **current repository snapshot** (not historical patch lines).

## Repository status (current snapshot)

### Actively used projects
- `PiSD/` — Pi-side driving runtime and web control
- `PiServer/` — modular Flask runtime and web dashboard for camera/motor/control/model operations
- `piTrainer/` — desktop trainer for driving models (steer/throttle)

### Reference/archive artifacts
- `PiBooter/`, `CustomTrainer/` and `CustomDrive/` — inactive as of 2026-11-24; existing code retained, no further development unless explicitly requested.
- Legacy piCar snapshots, if present, are reference only.
- `PiServer_0_3_4/`, `PiServer_0_4_1/`
- timestamped `.zip` snapshots at repo root

## Runtime/version markers found in code

- `PiSD/pisd/__init__.py` — PiSD version
- `PiServer/piserver/app.py` — PiServer version
- `piTrainer/piTrainer/version.py` — piTrainer version

See the [stabilization acceptance gate](docs/stabilization_acceptance.md) for the merged and pending versions at the recorded inspection date.

> If patch-note files mention newer numbers than the constants above, treat those patch notes as historical documentation unless matching code is present.

## Requirements matrix

| Project | Python | Install command |
|---|---|---|
| PiSD | Check PiSD README | `pip install -r PiSD/requirements.txt` |
| PiServer | 3.10+ (3.11 preferred) | `pip install -r PiServer/requirements.txt` |
| piTrainer | 3.10+ (3.11 preferred) | `pip install -r piTrainer/requirements.txt` |

Pi-only optional runtime dependencies include `picamera2`, `RPi.GPIO`, and `tflite-runtime`.

## Standard setup pattern

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

Then install the specific project requirements file.

## Launch commands (canonical)

- PiSD (simulation): `python PiSD/PiSD.py`
- PiServer: `python PiServer/server.py`
- piTrainer: `python piTrainer/main.py`

## Instructional docs index

- Engineering, refinement, and UI/UX update plans: [Development roadmaps](docs/roadmaps/README.md)
- Repository maintenance/process: `INSTRUCTIONS.md`
- Cross-project bug prevention guidance: `BUG_PREVENTION_NOTES.md`
- PiServer usage: `PiServer/README.md`
- PiSD usage: `PiSD/README.md`
- piTrainer docs: `piTrainer/README.md`
- [Stabilization and release acceptance](docs/stabilization_acceptance.md)

## Known doc-version caveat

Some `PATCH_NOTES/` files document attempted or forward patches that may not match this checkout exactly. Validate behavior against code constants and entry points before deploying.
