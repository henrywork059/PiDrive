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


## Revision 2.3 — effective YUV420 layout and preview delivery
Parent 1b02da5b22c35c2b31b04761e17f2d6ee6a44862 passed all ten jobs (Linux 46021196297, Windows 46021196279, strict 46021196288, short 46021196298). Strict camera artifact 15210630260 SHA256 2a5998f7ce4c0c5fef1fd3fc68e7471e22e14d7e69053aad3a66759b3cf9752c; short 15208098887 9f7e37aa1be124daf22cc184920509d74f73768222ce0b62eecc0d465b617c0b. PiServer strict inference -55.84%, concurrent -25.77%; reconnect duplicate sequences 22→0. No lowres-specific physical benefit inferred.
- piserver/services/preview_yuv.py validates actual configured YUV420 size/stride, decodes physical padding then crops the owned BGR result, rejects malformed arrays and mismatched formats. Source checked against upstream Picamera2 request.py and DRM planar offsets. Local 14/14 helper tests on Python/NumPy 2.3.5/OpenCV 4.13.0 (outside pinned CI versions), exact decoded pixels and JPEG bytes compared to packed reference. Five paired 1000-call 320x180/384-stride synthetic conversion median CPU 0.03440→0.02866 ms versus explicit plane repacking (not a prior production comparison).
- camera_service.py reads effective stream_configuration before start; unsupported metadata falls back to main; release stays under original capture lock, close attempted even when stop raises. Preview cadence uses monotonic clock, scheduled misses/attempts reported separately from recording, condition waits tolerate spurious notifications. Main stream, defaults, recording and AI unchanged. Added lifecycle and format/padding regressions; exact candidate CI pending. No version increment or physical acceptance.


### Resource evidence harness
Added separate five-pair mock request operation comparison and 60-second-per-mode capture-loop soak with slow preview subscriber, raw main-frame parity, request/release balance, latest-slot bounds, missed previews, RSS samples and age. No sensor/ISP/physical energy inference; low-resolution JPEG size and pixels intentionally differ. No new profile or safety/recording behavior. CI pending.


## Update 2.4 — reversible preview economy profile
Exact parent 458304862e45c5fd33b39cb0f6246a318e728a6c all 11 jobs passed; 60-second mock soak 1201/1201 releases, 601 previews, zero misses, one-slot bound; main/lores CPU 3.902→3.590s, JPEG median 49349→22756 bytes (different optional resolutions). Resource archive 15212256369 SHA256 242468b63587f751746f96f8ad29ff3535b741c544ac5fc99f7af62a14614383. Explicit economy caps only scheduled preview at 6 FPS and JPEG quality 40, never raises lower user settings, preserves stored configured values, raw acquisition cadence and recording/inference inputs. Standard restores on next eligible frame without restart. Existing camera API accepts profile-only updates and saves via existing config store, reports configured and effective values. Existing lores choice independent (profile does not reconfigure camera). Invalid profile-only values rejected; old configs default standard. New deterministic JPEG/config/capture-cadence regression registered; exact CI pending. No automatic activation, hardware acceptance or version promotion.

Operator control: web camera settings expose Standard/Economy, explicit Apply preview profile, live effective FPS/JPEG and separate saved/runtime confirmation; economy also caps browser snapshot polling, without changing existing Standard scheduling. Ordinary camera Apply remains separate. UI/browser qualification pending.

Resource qualification extension: 120 seconds per main/lores/lores-economy mode, output byte rate, configured/effective profile, CPU/RSS and preview age. Separate real service loop mock reconnect injects two request failures, asserts old/new device close/release balance and recovered main-frame parity. No real device or recording throughput claim; candidate results pending.

Profile UI readback mismatch now explicitly shown instead of reusing a potentially successful POST message. Native browser fixture checks visible/accessibly named profile, read-only selection, intercepted rejection, unchanged effective values, enabled retry/STOP, and captures new panel. Real API persistence test separate. Candidate CI pending.
