# PiSD 0.11.46 — Performance Update 1 draft candidate

Package baseline: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7

**Status:** provisional candidate version for complete forward-package CI, not published, stable, merged, or physically validated. Exact starting checkpoint 31f2226596e3552aacb4ce745ce72f50ca216af1 passed Linux 45992157666 (4/4) and Windows 45992157641 (1/1). Subsequent 6192e8f7 CI 45996881844 failed forward package selection because PiServer app.py was edited without a version change. Fix selection by using an explicit trusted baseline for the complete stacked milestone; preserve all strict archive, rollback, history and version checks. Current version reserved only after checking main/branch notes and open PRs.

## Changes
In-place normalization, same-dtype interpreter input reuse, visibility refresh coalescing, unchanged readiness tone guard, bounded wait on duplicate stopped-stream JPEGs, lock-protected scalar preview FPS read instead of a full settings deepcopy per viewer/frame. Shared JPEG remains required for AI/recording. Added input/stream/settings persistence checks.

## Verification and remaining limits
Read live source and previous checkpoint/version notes; the existing operation-level benchmark figures in the checkpoint are not hardware measurements. Exact paired benchmark and profiles are now scheduled by CI using the original and extended scripts; inspect actual artifacts and regressions before accepting this candidate. No device energy, physical STOP, full workload CPU/RSS or native visual signoff is claimed. Keep configuration and approved 105 web PNG reference unchanged. See the performance roadmap and component checkpoint notes for details.
