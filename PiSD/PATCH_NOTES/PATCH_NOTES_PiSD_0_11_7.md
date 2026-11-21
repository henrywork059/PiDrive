# PiSD 0.11.7 Patch Notes — AI stale-camera fail-safe

## Request summary
Implement the next roadmap improvement (U21): stop AI driving when capture frames stop advancing instead of repeatedly applying a cached prediction.

## Baseline and anti-rollback
Built on live GitHub PiSD `0.11.6` (not the older uploaded `0.11.0` archive).
Reviewed patch notes for 0.11.6, 0.11.5, 0.11.4 and 0.11.3.
Preserves three independent capture/preview/inference FPS settings, AI assist, one safety confirmation, saved manual speed, error panel, camera restart recovery, and existing recording metadata.

## Root cause
0.11.6 intentionally reuses the last AI model result when a camera sequence is unchanged, avoiding duplicate inference. However, a stalled capture source could keep that previous command active indefinitely because `command_timeout_s` was stored but not enforced against frame age.

## Files changed
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/__init__.py`
- `PiSD/scripts/test_ai_frame_timeout.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_7.md`

## Behavior
- Starts a monotonic freshness window when the first camera frame arrives.
- Refreshes the window only when a positive camera frame sequence changes.
- Allows duplicate-frame prediction reuse only within the saved `ai_mode.command_timeout_s` window (already clamped to 0.2–3.0 seconds).
- Rejects unknown/zero sequences once their initial grace period expires, rather than trusting them forever.
- On a stale frame, latches a safety fault until AI is explicitly restarted; recovering camera frames cannot silently re-arm driving.
- On a stale frame or prediction error, attempts an immediate motor stop and zeros cached AI raw, corrected, safe and motor commands so AI assist and labels do not reuse stale output.
- Exposes `camera_frame_age_s`, `camera_frame_timeout_s`, `camera_frame_stale`, and `camera_frame_fault_latched` in AI status.
- Leaves `camera.fps`, `camera.live_preview_fps`, and `ai_mode.update_hz` untouched.

## Verification
Added hardware-free unit tests for sequence timeout, advancing frames, unknown sequence, and stop/zero behavior. Static verification of changed source is required in CI or an environment with the current PiSD checkout. **Physical Raspberry Pi camera and motor tests have not been performed.**

## Known limits
This is a frame-freshness gate in the AI inference loop, not a second independent motor hardware watchdog. A blocking inference or service thread can still delay checking the next frame; an independent motor-level timeout remains a separate safety enhancement. Test real camera stall, disconnected camera, and AI assist behavior with wheels lifted before merging.
