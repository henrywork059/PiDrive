# PATCH NOTES - CustomDrive draft

## Goal
Create a first draft code scaffold for a **single competition mission**:

- drive to rough search area
- use object detection to find the target
- visually align and approach
- grab target
- drive to rough drop area
- visually align and approach drop zone
- release target
- repeat

## What is included
- modular Python package under `custom_drive/`
- state machine for one mission loop
- timed coarse route follower
- visual-servo controller for target centering and close-range approach
- fake robot for PC-side testing
- PiCar bridge draft for later integration
- runnable demo entry point

## What is intentionally still draft-only
- no real detector model is bundled
- no real gripper / servo hardware driver is bundled
- no direct Flask server wiring yet
- no obstacle handling yet
- no field calibration file yet

## Design choice
The control logic uses **coarse route + local visual servoing** instead of a single end-to-end driving model. This matches the mission strategy discussed earlier and should be easier to debug on the real field.

## Notes for next patch
- connect the real detector output
- connect real grab / release hardware
- add state + status endpoint for PiServer
- add retry / backup routine after failed pickup
- add simple IMU / encoder correction if available
