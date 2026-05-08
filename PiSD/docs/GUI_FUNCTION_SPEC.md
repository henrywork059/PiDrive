# PiSD GUI and Function Specification Draft

## Current GUI shell

The current page at `/` is a small hardware-service test shell.

It includes:

- camera preview image
- start/stop camera buttons
- steering slider
- throttle slider
- emergency stop button
- live JSON status panel

## Current API endpoints

```text
GET  /api/status
POST /api/camera/start
POST /api/camera/stop
GET  /api/camera/config
POST /api/camera/apply
GET  /api/camera/frame.jpg
GET  /video_feed
GET  /api/motor/config
POST /api/motor/apply
POST /api/control/manual
POST /api/control/stop
```

## Design goals

- fast loading
- clear control state
- safe default simulation mode
- obvious emergency stop
- no hidden backend failures
- all controls call real APIs

## Suggested future tabs

### Manual

- steering slider
- throttle slider
- steer mix
- reverse option
- trim controls
- speed limit
- stop button

### Camera

- preview start/stop
- resolution
- preview quality
- snapshot
- exposure/AWB controls
- camera restart

### Settings

- save settings
- reload settings
- reset defaults
- export/import later

### Diagnostics

- backend mode
- camera state
- motor state
- last error
- event log

### Full Auto / Lane Detection

Add later after the manual, camera, and motor layers are stable.
