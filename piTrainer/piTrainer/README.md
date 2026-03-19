# piTrainer Package Notes

This directory contains the internal Python package used by `../main.py`.

## Package structure

- `app.py` — application bootstrap and startup flow.
- `app_state.py` — shared runtime/app state container.
- `main_window.py` — top-level window shell and page wiring.
- `pages/` — page composition and feature-specific views.
- `panels/` — reusable panel/dock widgets.
- `services/` — business logic (data, preprocess, train, validation, export).
- `ui/` — style/theme and UI helper modules.
- `utils/` — cross-cutting utility helpers.

## Developer guidance

- Keep page-level UI code in `pages/` and shared widgets in `panels/`.
- Keep non-UI logic in `services/`.
- Store state transitions in `app_state.py` rather than ad-hoc globals.
- Prefer pure helper functions in `utils/` for reusable transformations.

## Where end users should start

For installation, launch steps, and workflow instructions, use the parent documentation:

- `../README.md`
