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

## 2026-11-28 — E04/E05 functional candidate

Main 7f8fcf5 includes #96 iframe restrictions, #102 storage feedback correction, and #104 stability fixes. Linux real browser manual-drive/STOP, settings quiet window and lifecycle already exercised; do not repeat those as unimplemented. This separate branch avoids overlapping #105 workspace presentation files. Added workspace-only recording/image replay and capture-failure injection at the real camera provider, scenario control page and real Keras service-level acceptance candidate. No boxes above are upgraded to complete until exact CI results and artifact/behavior review. Video replay, real AI page interactions, piTrainer import, other fault types, Windows live browser and broader release qualification remain open.

### E04/E05 continuation — 2026-11-28

Exact a0ab6514 passed all four workflows 46139136367, 46139136308, 46139136281, 46139136359. Direct logs: 13 adapter cases, 2 scenario cases and 1 actual Chromium case; six startup/explicit settings GETs and zero quiet/save/drive/STOP echoes. E04 scoped service-level AI/recording/image replay and E05 camera fault/rearm passed. Add local video replay, sticky virtual motor disconnect and actual AI-page/recording-download/relocated trainer service import candidate. New exact CI and rendered artifact audit pending. Other model/API/network/GPIO faults, cross-platform live qualification, custom environments and full E06 remain open. No change to #105 workspace files or stable acceptance.

### E04/E05 third checkpoint — 2026-11-28

Parent dd67c688 passed all four exact CI workflows. Independent artifact 15261113863 verified SHA256 5756edf8347b440d1f548074de0000f8751486b60cd71482a4082bfd7d21dff7, nested ZIP CRC and SHA, 12/12 frame hashes/label trace parity, four rendered screenshots and source sequences. E04 video, actual AI browser, relocated trainer loader passed scoped Linux gate; video/motor direct test logs passed but raw evidence absent in parent. New candidate adds raw video/motor evidence, model inference failure, heartbeat API failure, left/right virtual GPIO failure and real Chromium manual network loss. Faults sticky per runtime, no physical claims. E05 expanded candidate requires exact CI and artifact audit; E01/E02/E03/E06 outstanding broader acceptance remains.
