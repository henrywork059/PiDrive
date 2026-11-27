# PiServer 0.4.55 — Update 2.2 native preview resource candidate

Package baseline: 04c62e457060270a6f3398a703de0b9b393162fa
Original performance comparison baseline: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7

## Summary and cause
Explicit opt-in native YUV420 low-resolution Picamera2 preview, preserving main raw frame and recording input. Prior main-only preview encoded native full-resolution request image even where optional preview did not need the full main geometry. Existing preview publication uses a single slot but lacked consumer-skip diagnostics.

## Changes
- PiServer/piserver/services/camera_service.py: preview_source=main default, lores opt-in, preview_stream_width clamped 64..1920, even aspect-respecting dimensions. Capability attempt within Picamera2 creation; unsupported or missing decoder falls back to main, releases rejected devices, and records reason. Runtime low-resolution request conversions produce owned JPEG bytes before request.release; unexpected shape/encode errors circuit-break to main path until camera reopen, preserving full-resolution AI/recording.
- PiServer/piserver/app.py: provisional 0_4_55 marker only.
- PiServer/tests/test_camera_lowres_p2.py: fake camera tests of default, opt-in, ownership, rejection, conversion failure fallback and single-slot skip statistics.
- .github/workflows/regression.yml: mandatory PiServer regression coverage.
- docs/roadmaps/PiDrive_Performance_Optimization_Plan.md: evidence and incomplete acceptance.

## Verification and limits
Candidate code submitted for CI, no hardware energy, physical safety, sensor-specific low-resolution color, Qt or performance benefit claimed. Low-resolution preview intentionally changes optional display geometry, never main recording/AI pixels. Inherited safety, image quality, frame timing, lease and stale-stop behavior retained; main remains default. Full CI and forward-package validation pending. No merge or stable promotion.
