# PiSD F4 — restore legacy AI validation entrypoints (0.11.22)

## Request and cause
The original F4 roadmap identified missing imports from pisd.services.ai_correction and pisd.services.ai_safety in two validation commands. On the exact green integration candidate e90f78705222880e75f6da4c8f2a9d1ef41389f1 both scripts still reference those absent modules. Actual correction, timeout and limiter logic lives inside AIDriveService.

## Changes
- scripts/test_ai_mode_page.py and scripts/run_standard_validation.py: call the production service through a test-only adapter, retain existing numeric cases and verify actual manual-active/gain fields instead of the removed equation display field.
- scripts/ai_validation_math.py: temporary service fixture, deterministic monotonic time and previous-output seed; no duplicated safety policy, model load, motor object or physical camera.
- scripts/test_ai_validation_math.py: run both math checks and verify expiry, disabled correction and reverse limiter semantics.
- Repository regression workflow: run the new unit suite and both existing standalone commands in the disposable CI checkout in simulation only. No hardware flags.
- This note.

## Baseline and verification
Reviewed latest 0.11.22, R48, R47 and R46 notes, actual AI service and existing safety tests. No production runtime, configuration, UI or version change. Green integration PR #84 is preserved as parent. The existing import references were confirmed by source inspection; new commands and assertions require actual CI results. Other legacy source/API assertions may reveal further failures. F4 remains partial until both complete commands pass. Do not run the full API validation against a user's working configuration without first backing it up or using a disposable checkout. No hardware tested.
