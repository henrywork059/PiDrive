# PiServer — stabilization: camera freshness API test contract

## Request and cause
The first repository regression run (PR #81, https://github.com/henrywork059/PiDrive/actions/runs/45341112481) failed three access API cases with AttributeError because the shared DummyCamera fixture lacked get_raw_frame_age(). The actual camera service implements this method and returns None if no raw frame exists. This is a stale test fixture, not evidence of a physical camera failure.

## Baseline and anti-rollback
Stacked directly on pending PiServer 0_4_28 / R49 PR #78, commit 3a0213c95f9cd972b65f87c894177de5969f41fb. Reviewed 0_4_28, 0_4_27, 0_4_26 and 0_4_25 patch notes, current app status API, camera service and shared tests. Preserve the current runtime version, recent events, preflight, tracing, safety and saved settings. No runtime/config/UI changes or version bump for this test-only patch.

## Files changed
- tests/test_control_service.py: DummyCamera implements the real no-frame contract.
- tests/test_access_api.py: explicitly verify status reports a null frame age for the mocked camera.
- This patch note.

## Verification
Original failures reproduced in GitHub Actions, matching live source inspection. Corrected exact-branch tests have not yet executed. No physical hardware testing performed. Do not merge ahead of the parent stack; require CI and separate physical acceptance.
