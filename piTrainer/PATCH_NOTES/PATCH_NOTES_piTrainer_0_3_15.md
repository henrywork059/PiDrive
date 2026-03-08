# PATCH NOTES — piTrainer_0_3_15

## Fix
- Reworked Path Preview so the path now curves from the start point at the middle bottom toward the exact target endpoint.
- The curve endpoint now matches the click-edit target geometry more directly.

## Technical change
- Replaced the previous styled cubic path sampling with endpoint-driven path sampling.
- The path now uses the exact start/end mapping and bends outward progressively toward the target point.

## Packaging
- Patch-only zip.
- Same wrapper-folder style and same relative project paths.
