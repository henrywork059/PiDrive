# CustomDrive 0_4_8 Patch Notes

## Request summary
Adjust the Mission 1 “go to class 1” follow logic so it uses a simpler frame-zone rule:
- divide the frame into left and right regions
- if the target centre is on the **left**, turn left
- if the target centre is on the **right**, turn right
- if the target centre lies inside the **middle 10%** band, go straight forward
- keep moving forward toward the target instead of only rotating in place

## Cause / root cause
The `0_4_7` tracking loop still used a proportional horizontal error value and then derived steering from that continuous error.

That was better than `0_4_6`, but it still did not match the newer requested Mission 1 control rule, which is an explicit **three-zone** decision:
- left region
- center band
- right region

Also, the earlier interpretation of `center_tolerance_ratio=0.1` behaved more like a wider tolerance around the centre line, not the requested “mid 10% of the whole frame” rule.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_8.md`

## Exact behavior changed
### Mission 1 tracking zone logic
The AI tracking phase now classifies the detected target centre into one of three zones based on the frame width:
- **left**: target centre is left of the middle 10% band
- **center**: target centre lies within the middle 10% band
- **right**: target centre is right of the middle 10% band

### Steering behavior
The Mission 1 tracker now uses explicit zone-based steering:
- **left zone** → left turn command while still moving forward
- **right zone** → right turn command while still moving forward
- **center zone** → straight forward command

### Forward motion behavior
Forward motion remains active while tracking:
- in left/right zones, the car uses reduced forward throttle while turning
- in the center zone, the car uses the normal approach speed and drives straight toward the target

### Center-band interpretation
For Mission 1 target following, the existing `center_tolerance_ratio` setting is now interpreted as the **total width** of the center band.

So the default value `0.1` now means:
- the middle **10% of the full frame width** is the straight-ahead zone

## Verification actually performed
- inspected the shipped `0_4_7` Mission 1 tracking code directly
- confirmed it still used continuous proportional steering instead of the requested left/center/right region rule
- updated the Mission 1 tracking loop to explicit three-zone logic
- verified the patched file compiles successfully with Python

## Known limits / next steps
- live left/right behavior still depends on the real Pi motor wiring and the saved shared motor runtime settings on the vehicle
- this patch intentionally keeps the current simple visual tracker and does not add search behavior when class 1 is missing
- if you want, the next patch can expose the Mission 1 center-band percentage directly in the Mission 1 web UI with wording like “Straight zone width (%)” so it is clearer than the older `center_tolerance_ratio` name
