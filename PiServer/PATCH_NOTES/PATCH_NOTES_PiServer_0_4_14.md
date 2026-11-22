# PATCH NOTES — PiServer_0_4_14: Shared camera and motor ownership

## Request summary
Implement the next reliability roadmap update, U14: prevent PiServer and
CustomDrive from simultaneously opening/controlling the same Raspberry Pi
motor GPIO or camera hardware. Preserve all existing control and mission
features. This is a shared-service PiServer change, not a CustomDrive rewrite.

## Baseline and anti-rollback review
- Stable PiServer baseline: `0_4_0`; advances the existing `0_4_x` patch line.
- Built forward on pending PiServer PR #15 (`0_4_13`), itself stacked on
  PR #14 (`0_4_12`) and PR #9 (`0_4_11`).
- Compared current source and notes `0_4_13`, `0_4_12`, `0_4_11`, `0_4_10`
  (and prior `0_4_9` safety/camera history).
- Checked CustomDrive's latest Mission 1 note `0_5_16` and prior
  `0_5_15`, `0_5_14`, `0_5_13`, plus pending PR #11 for `0_5_17`.
  The shared PiServer services are imported directly in CustomDrive's
  GUI, manual, live, and Mission 1 runtime entry points.
- Preserves PiServer AWB defaults, model shape preflight, browser CSRF/access
  protection, manual deadman watchdog, and all UI layout/version keys.
- Preserves CustomDrive 100%-top/0%-bottom threshold semantics, mission stages,
  arm pose behavior and its existing config values; no CustomDrive files changed.

## Root cause / risk
Both PiServer `create_app()` and CustomDrive live entry points instantiate
`CameraService()` and `MotorService()` from the same PiServer code. Neither
runtime previously held a cross-process ownership lease before initializing
GPIO or Picamera2. Two active services could contend and send conflicting
physical motor instructions. This was a static code risk; no real collision
was observed on the user's Raspberry Pi.

## Files changed
- `PiServer/piserver/core/hardware_ownership.py` (new)
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/tests/test_hardware_ownership.py` (new)
- `PiServer/piserver/app.py` (version only)
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_14.md` (new)

## Exact behavior changed
1. Raspberry Pi camera and motor adapters share one POSIX `flock` lease
   file (`/tmp/pidrive-physical-hardware.lock` by default, or the common
   absolute `PIDRIVE_HARDWARE_LOCK_FILE` environment override).
   The file's inode remains stable; the lock file is not deleted on release.
2. Camera and motor can each claim a resource **once per process**, sharing
   the same process-level lease. Another process attempting either resource
   fails promptly with an actionable ownership-conflict message.
3. Motor service acquires ownership **before** any GPIO setup/PWM initialization.
   Startup failure releases its lease only after best-effort cleanup.
4. Camera service acquires ownership **before** physical Picamera2/OpenCV open
   on Raspberry Pi. Desktop/simulation mode without Pi hardware continues
   without an OS lease. Capture restart reacquires only after clean shutdown.
5. A failed camera thread join does not release ownership; restart is refused
   while that thread is still alive. A failed GPIO cleanup also retains the
   motor lease rather than silently permitting another owner.
6. Motor `close()` is idempotent: it writes zero output and cleans up GPIO
   before releasing ownership. A closed service rejects new motor commands
   and cannot clean up hardware belonging to a replacement service.
7. New motor construction starts PWM at zero; no previous state is restored.
   The existing manual-command watchdog and safety checks remain intact.
8. `APP_VERSION` advances to `0_4_14` for consistency and cache busting,
   with no persistent runtime/config migration or change to UI layout.
9. CustomDrive automatically inherits this mechanism when it imports the
   updated PiServer service classes; no duplicate implementation is added.

## Verification actually performed
Against the live GitHub-compatible PiServer service sources from the uploaded
PiDrive archive (exact Git blob hashes checked before edits):
- `python -m unittest discover -s tests -q`: **43 tests passed**, including
  **8 new ownership tests** with no Raspberry Pi hardware.
- `python -m compileall -q piserver tests server.py`: passed.
- New tests cover two owners in one process, cross-process denial, process
  crash/lock recovery, GPIO reinitialization, rejected motor updates after
  close, initial GPIO failure, failed GPIO cleanup, camera-before-motor
  acquisition, hung camera thread, and desktop simulation behavior.
- Exact Git blob hashes for all four new/edited service/test Python files
  are matched to the code that passed the local suite.
- Confirmed CustomDrive live/manual/GUI/Mission 1 source uses PiServer's
  shared MotorService and CameraService, not a separate hardware adapter.

## Known limits and next steps
- **No Raspberry Pi physical tests performed**. Before merging, run the full
  stacked 0_4_11 through 0_4_14 suite with Flask installed and test cross-
  runtime launch/handover with wheels raised and real Picamera2/GPIO.
- The lease is an advisory software lock; older/unpatched PiSD, third-party
  GPIO programs, and other camera processes that ignore the lease can still
  interfere. Follow-up should coordinate PiSD and external hardware owners.
- A process crash releases the flock automatically, but this is **not** a
  physical motor deadman switch. Independent hardware timeout is needed.
- This patch does not implement remote PiServer command routing for CustomDrive
  or an operator-controlled zero-downtime handover; it implements exclusive
  standalone hardware ownership as the first safety layer.
- Both runtimes must use the same lock-file location and filesystem.
- Merge PRs #9, #14, #15 and then this PR in order, after safety validation.
