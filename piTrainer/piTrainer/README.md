# piTrainer package notes

This folder contains the main application package used by `../main.py`:

- `app.py`: app bootstrap and startup flow.
- `app_state.py`: shared runtime state container.
- `main_window.py`: shell window and page wiring.
- `pages/`: page-level composition.
- `panels/`: reusable dock/panel widgets.
- `services/`: business logic (data, preprocess, train, validation, export).
- `ui/`: styles and UI helpers.
- `utils/`: utility helpers.

For setup and end-user workflow, see `../README.md`.
