# PiSD Directory, File, and Patch Instructions

## Purpose

This document records how the `PiSD/` folder should be developed so it remains a clean test path for improving PiServer GUI and functions.

## Top-level rules

- Keep all PiSD work inside `PiSD/`.
- Do not modify `PiServer/` from a PiSD patch unless explicitly requested.
- Do not copy old PiServer files blindly.
- Use PiServer as a behavior reference, then rebuild in PiSD with clearer boundaries.
- Keep only one Python dependency file: `PiSD/requirements.txt`.
- Keep all patch notes in `PiSD/PATCH_NOTES/`.

## Folder instructions

### `PiSD.py`

Main launcher only. It should parse CLI flags and call the package app factory.

Do not place large service logic here.

### `config/`

Stores safe default settings.

Rules:

- keep defaults conservative
- do not store user runtime data here unless a future config store is intentionally added
- preserve backward compatibility when adding keys

### `pisd/app.py`

Owns Flask route wiring and simple web GUI shell.

Rules:

- route handlers should call services
- route handlers should not directly control GPIO or camera hardware
- every hardware action should return clear JSON status

### `pisd/services/`

Owns real runtime behavior.

Current services:

- `camera_service.py`
- `motor_service.py`

Rules:

- each service must have simulation fallback
- no service should crash on a PC just because Raspberry Pi libraries are missing
- hardware should be opt-in through the launcher until safety is verified

### `pisd/core/`

Small shared helpers only.

Rules:

- keep helpers generic
- avoid UI or hardware code here

### `docs/`

Planning and instruction documents.

Rules:

- update docs when run commands, paths, endpoints, or service behavior changes
- remove stale instructions instead of leaving multiple conflicting commands

### `PATCH_NOTES/`

One patch note per package version.

Patch notes must include:

- request summary
- cause/root cause if known
- files changed
- behavior changed
- verification actually performed
- known limits or next steps

## Patch packaging instructions

For PiSD patch zips:

- preserve exact folder structure beginning with `PiSD/`
- include the full PiSD starter component unless the user requests patch-only delivery
- do not add extra nesting such as `PiSD_0_0_1/PiSD/`
- do not include unrelated PiDrive folders

## Anti-rollback checks

Before packaging:

- confirm `requirements.txt` is the only dependency file
- confirm `PiSD.py` still launches the app
- confirm `/api/control/stop` still exists
- confirm camera and motor services still have simulation fallback
- confirm docs do not reference removed `requirement.txt`
