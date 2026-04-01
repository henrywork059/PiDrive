# CustomDrive 0_4_7 Patch Notes

## Request summary
Adjust the new Mission 1 session web GUI target-follow behaviour so the car more reliably drives toward **class 1** after the start route. Specifically:
- review whether the go-to-target turning direction was reversed
- make sure the car keeps moving forward toward the target instead of only rotating/waiting

## Cause / root cause
The initial `0_4_6` Mission 1 target-follow implementation used image-space horizontal error directly as motor steering input.

In the shared `MotorService` differential-drive mix, that sign is not the same as the camera-frame left/right sign for “drive toward target”, so the Mission 1 follow step could steer the wrong way depending on target position.

Also, the initial implementation set throttle to zero whenever the target was outside the center tolerance. That made the robot stop forward motion during most of the alignment phase, which was too conservative for a “go to class 1” behaviour.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_7.md`

## Exact behavior changed
### Mission 1 target-follow steering
- inverted the target-follow steering sign used in the AI tracking phase so a target appearing on the right side of the frame produces a rightward steering arc through the shared `MotorService`
- left the existing PiServer `steering_direction` runtime config support intact, so user-configured steering inversion is still respected

### Mission 1 forward motion while tracking
- changed AI tracking so the car now continues moving forward while steering toward the detected target
- when the target is far from centre, the car now uses a reduced forward throttle instead of stopping completely
- when the target is near centre, it uses the configured `approach_speed`

## Verification actually performed
- inspected the shipped `0_4_6` Mission 1 follow logic and the shared `PiServer/piserver/services/motor_service.py` differential-drive mapping
- confirmed the old `0_4_6` sign and throttle behaviour were inconsistent with the intended “drive toward class 1” behaviour
- updated the Mission 1 session app and ran Python compilation for the patched file successfully

## Known limits / next steps
- live steering direction still depends on the real vehicle wiring and the saved PiServer `steering_direction` runtime setting on the Pi
- if the physical vehicle still turns opposite to expectation on hardware, the next patch should add an explicit Mission 1-only “tracking steering invert” option in the Mission 1 config/UI instead of relying only on the shared motor runtime setting
- the current tracking remains a simple proportional image-centre follower; it does not yet estimate range beyond bounding-box position/size
