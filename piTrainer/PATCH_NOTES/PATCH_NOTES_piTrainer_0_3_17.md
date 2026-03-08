# PATCH NOTES — piTrainer_0_3_17

## Changes
- Replaced the path curvature math with a quarter-ellipse arc instead of the earlier two-control-point cubic curve.
- Kept the same start point (mid-bottom) and the same steering/speed target endpoint.

## Details
- Path Preview now samples a 1/4 ellipse from the anchor point to the target point.
- The path starts vertically from the car position and bends into the target point like a clearer turning arc.
- The endpoint still matches the same click-edit / steering-speed mapping.
- Near-zero steering safely falls back to a straight path.

## Verification
- Python compile check passed on the patched file.
- Patch zip contains only changed files with the same wrapper-folder structure as before.
