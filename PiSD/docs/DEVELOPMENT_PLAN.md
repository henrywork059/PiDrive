# PiSD Development Plan

## Phase 0 — Starter scaffold

Completed in `PiSD_0_0_0`:

- placeholder launcher
- documentation
- possible package list
- patch notes

## Phase 1 — Real service shell

Completed in `PiSD_0_0_1`:

- single `requirements.txt`
- directory/file instructions
- camera service with Picamera2 path and simulation fallback
- motor service with RPi.GPIO-style path and simulation fallback
- temporary web GUI controls
- API endpoints for status, camera, and manual motor control

## Phase 2 — Persistent settings

Next recommended work:

- add `settings_service.py`
- save user runtime settings safely
- reload settings at startup
- validate and clamp config keys
- add reset/export/import settings endpoints

## Phase 3 — Camera tools

Suggested work:

- snapshot folder setting
- save current frame as image
- capture sequence tool
- preview quality selector
- camera restart/apply button in GUI
- camera diagnostics panel

## Phase 4 — Better GUI layout

Suggested work:

- split HTML/CSS/JS into files
- tabs for Manual, Camera, Settings, Diagnostics
- persistent layout later
- mobile/tablet-friendly controls

## Phase 5 — Recorder and training data path

Suggested work:

- dataset/session folder service
- frame capture metadata
- steering/throttle logging
- zip/export tool

## Phase 6 — AI/autonomy

Add only after camera and motor basics are stable:

- model service
- simulated model output
- TFLite adapter
- lane detection adapter
- runtime timing display
- safe fallback to manual mode

## Merge decision

PiSD should not replace PiServer until the user explicitly decides to merge or promote it.
