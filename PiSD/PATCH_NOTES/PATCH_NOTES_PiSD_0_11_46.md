# PiSD 0.11.46 — Performance Update 1 draft candidate

Package baseline: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7

**Status:** provisional candidate version for complete forward-package CI, not published, stable, merged, or physically validated. Exact starting checkpoint 31f2226596e3552aacb4ce745ce72f50ca216af1 passed Linux 45992157666 (4/4) and Windows 45992157641 (1/1). Subsequent 6192e8f7 CI 45996881844 failed forward package selection because PiServer app.py was edited without a version change. Fix selection by using an explicit trusted baseline for the complete stacked milestone; preserve all strict archive, rollback, history and version checks. Current version reserved only after checking main/branch notes and open PRs.

## Changes
In-place normalization, same-dtype interpreter input reuse, visibility refresh coalescing, unchanged readiness tone guard, bounded wait on duplicate stopped-stream JPEGs, lock-protected scalar preview FPS read instead of a full settings deepcopy per viewer/frame. Shared JPEG remains required for AI/recording. Added input/stream/settings persistence checks.

## Verification and remaining limits
Read live source and previous checkpoint/version notes; the existing operation-level benchmark figures in the checkpoint are not hardware measurements. Exact paired benchmark and profiles are now scheduled by CI using the original and extended scripts; inspect actual artifacts and regressions before accepting this candidate. No device energy, physical STOP, full workload CPU/RSS or native visual signoff is claimed. Keep configuration and approved 105 web PNG reference unchanged. See the performance roadmap and component checkpoint notes for details.

## Strict measured continuation

Eight-second hardware-free attribution at 32d710d: 162 simulated-frame calls consumed 89.58 ms inclusive thread CPU, encoding 37.8 ms; idle CPU 20.71→22.09 ms/s, target not met. Reuse dimension-keyed static simulation gradient and apply identical NumPy uint8 scalar arithmetic through a 256-entry LUT; each publication still owns fresh pixels and JPEG. Local isolated 426×240 fixture, NumPy 2.3.5/OpenCV 4.13.0 (outside declared range), sequences 0–36 pixel-exact; five paired medians 0.4132→0.2949 ms for sequence 25. Supported NumPy 1.x boundary/large-sequence parity, resize, fallback and long workload CI pending. Hardware request/array paths, cadence and frame ownership unchanged. No physical idle savings claim.
Exact parent 32d710d passed Linux 46001881327, Windows 46001881366, strict 46001881398 and short workload 46001881331 (8/8 jobs). Version marker and original package baseline unchanged; no acceptance target waived.

### Strict continuation — owned channel assembly and request capture

Exact parent bd7c49b: PiSD/PiServer/trainer regression, manifests/packages and Windows passed; new short matrix 140/140. Local five paired isolated simulation tests (NumPy 2.3.5/OpenCV 4.13.0 outside declared range, sequences 0–36) using existing gradient and text, exact raw pixels and encoded JPEG bytes: 426×240 frame CPU 0.22212→0.15796 ms, frame+JPEG 0.40587→0.34708 ms; 640×480 frame 0.45871→0.24669 ms, frame+JPEG 0.98206→0.76690 ms; 160×120 essentially unchanged. Use OpenCV merge of broadcast narrow channels plus existing LUT, with explicit uint8 cast preserving NumPy 1.x promotion and independent frame ownership, NumPy fallback if OpenCV merge fails. Added JPEG-byte parity and forced fallback regression. Do not reduce FPS, preview quality, shared JPEG or raw contract.

PiSD request path uses the same redundant PIL-to-BGR copy as previously optimized and qualified PiServer. Local paired RGB conversion 0.43840→0.06499 ms, RGBA 0.40101→0.04707 ms with exact pixels and owned writable output. Apply guarded np.asarray + cvtColor, NumPy fallback, unchanged request JPEG/metadata/release. Added all-mode parity, explicit failure fallback and release-on-exception tests. New independent strict fake Picamera2 request job exercises actual capture/metadata/record/inference/viewer code paths, exact raw/JPEG fixture and capture/release counts, five matched 8-second idle/concurrent pairs, without touching hardware. This is additional evidence, not a replacement for simulation or physical-device qualification. All new supported-environment regressions and workload results pending; version, config, UI, safety and prior fixes retained.
