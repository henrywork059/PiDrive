# PiSD GUI and Function Specification Draft

## Current GUI shell

`PiSD_0_2_1` provides a temporary testing server GUI at `/` and `/testing`; `PiSD_0_2_2` adds stronger GUI/API validation and a safe browser smoke-test button.

This page is intentionally not the final driving UI. It is a browser-based API and settings tester for checking backend service behaviour before the actual PiServer-style GUI is designed.

It includes:

- camera preview and camera service buttons
- camera settings apply form
- motor settings apply form
- one-by-one motor channel test panel
- custom API caller
- safe browser smoke-test button
- status / last response / error-code panels
- emergency stop button

## Current API endpoints

```text
GET  /api/test-gui/manifest
GET  /api/status
POST /api/camera/start
POST /api/camera/stop
GET  /api/camera/config
POST /api/camera/apply
GET  /api/camera/frame.jpg
GET  /video_feed
GET  /api/motor/config
POST /api/motor/apply
POST /api/motor/test-channel
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


## Testing GUI behaviour

The testing GUI should only prove API and settings behaviour. Do not add final layout/docking/recording/model features here yet. The final GUI should be built later after these calls are confirmed stable.

Motor movement remains locked by default. `/api/motor/test-channel` must continue to refuse real output with `PISD-MOT-008` unless `enable_motor_output` is true. The safe smoke-test button must never arm real motor output; it should accept either a safe simulation run or the expected `PISD-MOT-008` refusal in hardware mode.
