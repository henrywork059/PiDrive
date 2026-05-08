# PiSD Architecture Notes

## Purpose

PiSD should let us rebuild the PiServer-style control stack from a clean foundation while preserving the existing PiServer as a working reference.

The first design should be simulation-first, then hardware-backed.

## Proposed layers

```text
PiSD.py
└── future app package
    ├── web_ui/              # HTML/CSS/JS GUI
    ├── api/                 # Flask/FastAPI route layer
    ├── services/            # camera, motor, recorder, model, autonomy
    ├── adapters/            # simulated adapters and Raspberry Pi hardware adapters
    ├── config/              # defaults and schema helpers
    ├── state/               # runtime status and event history
    └── tests/               # smoke and behavior tests
```

## Layer rules

### GUI layer

The GUI should only call APIs and display state. It should not directly own hardware logic.

### API layer

The API should validate input, call services, and return clear JSON responses. It should not hide failures.

### Service layer

Each major function should have its own service:

- camera service
- motor service
- model service
- recorder service
- settings service
- autonomy service

### Adapter layer

Every hardware-facing function should have two adapters:

- simulated adapter for PC and safe testing
- Raspberry Pi adapter for live hardware

This lets GUI and API work continue even when the Pi camera, GPIO, or motor driver is not available.

## First implementation target

The first real PiSD version should add these modules before adding complex AI/autonomy:

1. `config/defaults.json`
2. `pisd_app/__init__.py`
3. `pisd_app/api/status.py`
4. `pisd_app/services/runtime_state.py`
5. `pisd_app/web_ui/templates/index.html`
6. `pisd_app/web_ui/static/app.js`
7. `pisd_app/web_ui/static/styles.css`
8. `tests/test_status.py`

## Compatibility rule

Do not copy old PiServer files blindly. Use PiServer as a reference, but rebuild in PiSD with clearer module boundaries and tests.
