# PiSD Runtime Settings Manager

PiSD 0.2.10 adds a backend settings manager so important UI and runtime settings are saved once and reused by every tab.

## Settings file

Runtime settings are stored in:

```text
PiSD/config/runtime_settings.json
```

This file is user-local runtime data. It should not be casually overwritten by future patch zips.

## Settings groups

The backend accepts these top-level groups:

- `camera` — camera settings passed to `CameraService.apply_settings()`.
- `motor` — motor settings passed to `MotorService.apply_settings()`.
  PiSD 0.8.1 motor settings include `steering_mode`, `turn_curve`, `min_inside_speed`, and `allow_pivot_turn` for the turn-rate steering algorithm, while keeping `steer_mix` for `arcade_mix` fallback mode. Legacy persisted `turn_gain` values are ignored for compatibility.
- `manual_drive` — manual drive defaults such as drag-pad speed and steer strength.
- `panel_presentation` — shared visual style used by all pages.
- `safety` — GUI safety defaults.
- `ui` — shared UI behaviour such as compact headers.

## API

```text
GET  /api/settings
GET  /api/settings/schema
POST /api/settings
POST /api/settings/apply
POST /api/settings/reset
```

All responses include `ok`, `code`, and `message`. Invalid payloads return a `PISD-SET-*` code instead of crashing.

## Browser behaviour

Pages still cache presentation settings in browser storage so styling can apply immediately, but `/api/settings` is the source of truth when the server is available.

The Settings page should be used for global defaults. Panel Presentation remains a style tuning page and now also saves through the backend settings API.
