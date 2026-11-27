# PiServer 0.4.54 — Performance Update 1 draft candidate

Package baseline: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7

**Status:** provisional candidate version for complete forward-package CI, not published, stable, merged, or physically validated. Exact starting checkpoint 31f2226596e3552aacb4ce745ce72f50ca216af1 passed Linux 45992157666 (4/4) and Windows 45992157641 (1/1). Subsequent 6192e8f7 CI 45996881844 failed forward package selection because PiServer app.py was edited without a version change. Fix selection by using an explicit trusted baseline for the complete stacked milestone; preserve all strict archive, rollback, history and version checks. Current version reserved only after checking main/branch notes and open PRs.

## Changes
Owned float normalization and same-dtype interpreter input reuse; avoid unused placeholder construction; skip repeated MJPEG sequence and unchanged preview-health writes. Added parity, idle placeholder and MJPEG tests. No raw/snapshot, STOP, camera capture timing or control lease changes.

## Verification and remaining limits
Read live source and previous checkpoint/version notes; the existing operation-level benchmark figures in the checkpoint are not hardware measurements. Exact paired benchmark and profiles are now scheduled by CI using the original and extended scripts; inspect actual artifacts and regressions before accepting this candidate. No device energy, physical STOP, full workload CPU/RSS or native visual signoff is claimed. Keep configuration and approved 105 web PNG reference unchanged. See the performance roadmap and component checkpoint notes for details.

## Strict measured continuation

Eight-second concurrent attribution at 32d710d: PIL conversion 141.04 ms for 163 calls; concurrent CPU 50.57→52.02 ms/s, target not met. Avoid redundant Pillow array copy and use OpenCV RGB/RGBA→BGR on standard uint8 images with exact NumPy fallback. Output remains writable and owned; preview PIL encoding unchanged. Local five-pair isolated 426×240 RGB conversion parity, NumPy 2.3.5/OpenCV 4.13.0/Pillow 12.3.0 outside declared range: 0.4820→0.1326 ms. Added supported-environment mode, fallback and ownership tests; long workload qualification pending.
Exact parent 32d710d passed Linux 46001881327, Windows 46001881366, strict 46001881398 and short workload 46001881331 (8/8 jobs). Version marker and original package baseline unchanged; no acceptance target waived.

### Strict evidence and regression repair

Exact parent 27bf0d3: eight of nine jobs passed; Linux PiServer job 140539966837 failed the newly added PIL parity test at import (ModuleNotFoundError: PIL), not an observed pixel mismatch. Add Pillow>=10,<12 to PiServer's regression-only dependency matrix, matching the dedicated workload CI; keep the test mandatory. Long actual artifact 15202887355: median concurrent process CPU 56.78→41.38 ms/s (-27.1%, every pair improved), inference 31.58→11.88 ms/s (-62.4%); identical median capture/record/inference counts. Concurrent inference sample age 38.93→39.92 ms; separate inclusive PIL conversion CPU 188.46→49.23 ms across 163 calls. Short artifact 15203336265 tested exact parent and retained zero candidate reconnect duplicates (22→0), with age p95 202.21→40.17 ms. No further production PiServer change justified. Full CI must rerun the repaired parity test before requalification; no physical-device claim or version change.
