# PiSD Development Plan

## Main idea

PiSD is a clean workspace for testing a better PiServer GUI and runtime design without risking the current working PiServer component.

## Phase 0 — Scaffold

Included in this package:

- `PiSD.py` placeholder launcher
- possible package list
- README
- architecture notes
- GUI/function plan
- test plan
- patch notes

## Phase 1 — Web GUI shell

Goal: build a responsive GUI with no real hardware dependency.

Suggested panels:

- status panel
- camera preview placeholder
- manual control panel
- mode selector
- settings panel
- log/event panel
- diagnostics panel

Expected result:

- page loads quickly
- layout is stable on desktop/tablet
- API polling is visible and controlled
- unavailable functions show clear messages

## Phase 2 — Runtime state and settings

Goal: make settings real and persistent from the start.

Suggested work:

- runtime state object
- safe settings schema
- load/save JSON helper
- default values
- validation and clamping
- reset-to-default button

Expected result:

- GUI changes update backend state
- saved settings survive restart
- bad config values do not crash the app

## Phase 3 — Simulation adapters

Goal: test motor, camera, and control logic safely before touching hardware.

Suggested work:

- simulated camera frame generator
- simulated motor state
- simulated steering/throttle limits
- fake model inference output

Expected result:

- all GUI buttons and sliders can be tested on PC
- status endpoint reports realistic simulated states
- no Raspberry Pi-only package is required

## Phase 4 — Camera pipeline

Goal: rebuild preview and snapshot behavior carefully.

Suggested work:

- camera adapter interface
- simulated camera adapter
- Picamera2 adapter
- frame format logging
- preview quality options
- snapshot save path rules

Expected result:

- no repeated stale snapshot bug
- live preview and saved image use the correct current frame
- camera restart behavior is explicit

## Phase 5 — Motor/control pipeline

Goal: rebuild manual control and runtime motor settings safely.

Suggested work:

- motor adapter interface
- simulated motor adapter
- real GPIO/motor adapter
- steering calibration
- throttle calibration
- reverse behavior
- emergency stop path

Expected result:

- UI values match real backend values
- saved calibration is actually applied
- emergency stop is always available

## Phase 6 — AI/autonomy tests

Goal: add autonomy only after GUI, state, camera, and motor basics are stable.

Suggested work:

- model adapter interface
- fake model adapter
- TFLite model adapter
- lane/debug overlays
- inference timing display
- autonomy enable/disable guard

Expected result:

- manual mode remains responsive
- AI mode can be disabled cleanly
- latency and failure reasons are visible

## Phase 7 — Decide merge strategy

After PiSD becomes stable, choose one path:

1. merge selected PiSD ideas back into `PiServer/`, or
2. promote PiSD into the next Pi-side server component.

Do not replace PiServer until PiSD has real feature parity and testing evidence.
