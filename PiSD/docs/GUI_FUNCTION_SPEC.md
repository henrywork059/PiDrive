# PiSD GUI and Function Specification Draft

## Design goals

- fast loading
- clear control state
- low-latency preview path
- obvious safety controls
- no hidden backend failures
- settings that actually apply
- simulation-first development

## Suggested main tabs

### 1. Manual

Purpose: direct driving control.

Possible controls:

- steering slider
- throttle slider
- stop button
- reverse enable/disable
- trim controls
- speed limit
- steering direction toggle

### 2. Camera

Purpose: preview and camera configuration.

Possible controls:

- preview start/stop
- preview resolution
- preview quality
- snapshot button
- snapshot folder display
- AWB/exposure controls later
- camera restart button

### 3. Full Auto

Purpose: autonomy test mode.

Possible controls:

- enable/disable autonomy
- model selection
- inference FPS display
- confidence/debug output
- safe fallback to manual mode

### 4. Lane Detection

Purpose: focused lane detection testing.

Possible controls:

- enable overlay
- threshold settings
- ROI controls
- debug image mode
- timing display

### 5. Settings

Purpose: persistent runtime settings.

Possible controls:

- save settings
- reload settings
- reset defaults
- export settings
- import settings later

### 6. Diagnostics

Purpose: show what is actually happening.

Possible displays:

- backend status
- camera state
- motor state
- model state
- API errors
- recent events
- hardware adapter mode

## API-first rule

Every GUI control should call an API endpoint or update state through a clear service. Avoid UI-only controls that look successful but do not change backend behavior.

## First API endpoints to build after this placeholder

```text
GET  /api/status
GET  /api/settings
POST /api/settings
POST /api/control/stop
POST /api/control/manual
GET  /api/camera/state
POST /api/camera/preview
POST /api/camera/snapshot
GET  /api/logs/recent
```

## Safety behavior

Emergency stop must remain visible in all drive-related tabs.

When a hardware function is unavailable, the GUI should show:

- unavailable function name
- likely reason
- current fallback mode
- next check/action
