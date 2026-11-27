# PiSD Emulator Roadmap

Milestones are functional checkpoints. This component does not increment a version for each small change.

## E01 — Architecture and virtual hardware foundation

**Status: Implemented; live HTTP launch still needs environment verification.**

- [x] Separate launchable emulator component in the PiDrive monorepo.
- [x] Launch the actual PiSD app factory without creating a copy of the server or pages.
- [x] Keep emulator configuration, model uploads, and recordings in a separate workspace.
- [x] Add a virtual motor sink after PiSD motor mapping, calibration, and safety processing.
- [x] Expose virtual GPIO pins, direction, duty cycle, and PWM frequency.
- [x] Prevent hardware mode when the emulator adapter is requested.
- [x] Add deterministic physics and service-boundary checks that run without Raspberry Pi hardware.
- [ ] Verify the live app starts and shuts down on Windows and Linux with PiSD requirements installed.

## E02 — Driving simulation and camera

**Status: Core implemented; live closed-loop browser verification remains.**

- [x] Fixed 60 Hz differential-drive movement from PiSD's mapped logical motor outputs.
- [x] Acceleration, braking, motor delay, per-wheel efficiency, and dead-zone settings.
- [x] Deterministic straight, left, right, S-curve, and circular track geometry.
- [x] Track boundary and obstacle collision status.
- [x] Generate perspective road scenes from current vehicle position and heading.
- [x] Supply generated frames through PiSD's existing camera capture service and JPEG pipeline.
- [x] Apply supported camera resolution, frame-rate, brightness, contrast, saturation, and flip settings.
- [ ] Test camera apply/restart through the actual PiSD Settings and Manual Drive pages.
- [ ] Verify a manual browser command moves the vehicle and changes a later PiSD camera frame.
- [ ] Add full track selection, configurable lane/road markings, environmental lighting, and saved custom scenarios.

## E03 — Emulator control workspace

**Status: Initial workspace implemented; browser verification pending.**

- [x] Start, stop, and restart PiSD; choose its local port.
- [x] Embed the actual PiSD Manual Drive page and offer a direct browser link.
- [x] Show a top-down view, first-person frame, motor outputs, virtual GPIO/PWM, and runtime events.
- [x] Add pause, fixed-step, reset, speed scale, and viewport presets.
- [ ] Capture and inspect real browser screenshots at desktop, tablet, and mobile sizes.
- [ ] Add runtime log export, API request history, performance charting, browser console capture, and test evidence export.
- [ ] Test app lifecycle on Windows and Linux.

## E04 — AI and recording

**Status: PiSD service paths are connected; behavior is unverified with a model.**

- [x] Use the actual PiSD `AIDriveService` and safety limiter with the virtual camera and motor sink.
- [x] Use emulator workspace model and recording directories.
- [x] Mark generated PiSD recording/snapshot manifests as synthetic while keeping trainer labels compatible.
- [ ] Load and run a compatible `.tflite` or `.keras` model through the actual AI page.
- [ ] Compare raw predictions, safety-limited outputs, motor outputs, and vehicle motion.
- [ ] Validate recording start/stop, image-label synchronization, dataset download, and piTrainer import.
- [ ] Add replay inputs for PiSD recording sessions, image sequences, and local driving videos.

## E05 — Fault injection and browser automation

**Status: Planned.**

- [ ] Inject camera, motor, GPIO, model, API, and network failures at their real service boundaries.
- [ ] Verify safe motor states and PiSD error reporting after each fault.
- [ ] Add scripted, reproducible fault scenarios.
- [ ] Add Playwright tests against the actual PiSD pages and interactions.
- [ ] Support headless CI, screenshots, logs, and structured test reports.

## E06 — Release qualification

**Status: Planned.**

- [ ] Run PiSD and emulator regression suites.
- [ ] Demonstrate manual and AI closed-loop driving.
- [ ] Verify configuration isolation and no physical GPIO access.
- [ ] Complete Windows workflow and Linux compatibility checks.
- [ ] Document known limits, installation, and a release acceptance report.

## Next work item

Run the live Flask app on a machine with PiSD requirements installed, test Manual Drive → MotorService → virtual vehicle → CameraService → actual PiSD preview, and record screenshots plus safe STOP evidence. Then implement Playwright browser coverage.
