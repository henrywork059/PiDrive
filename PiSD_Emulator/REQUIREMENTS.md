# PiSD Emulator Requirement Tracker

Status meanings: **Implemented, unverified** means code and a local unit/service test exist, but the complete live/browser flow has not been demonstrated. **Partial** means only the stated subset is present. **Planned** means not implemented.

## Mandatory acceptance criteria

| # | Acceptance criterion | Status | Evidence or remaining work |
|---:|---|---|---|
| 1 | PiSD runs without physical hardware | Implemented, unverified | Emulator calls the real app factory with `hardware_enabled=False`; live Flask runtime not launched in this environment. |
| 2 | Actual PiSD HTML interface is accessible and functional | Implemented, unverified | Control page embeds PiSD `/manual-drive`; needs live browser check. |
| 3 | Virtual camera provides a moving driving scene | Partial | Renderer scene changes with engine pose and is wired into CameraService; cross-service HTTP frame display not browser-verified. |
| 4 | Manual driving changes vehicle position | Implemented, unverified | Manual requests use PiSD MotorService whose mapped outputs update the engine; requires live browser action. |
| 5 | Vehicle movement changes following camera images | Implemented, unverified | Renderer unit check confirms frame pixels change after motion; camera integration needs live HTTP check. |
| 6 | AI predictions drive the virtual vehicle through PiSD | Partial | Existing AIDriveService is connected to camera and motor services; requires compatible model and runtime check. |
| 7 | Motor tuning changes simulated output and movement | Implemented, unverified | MotorService output hook receives channel and timed-test results; live UI test remains. |
| 8 | Camera settings affect generated frames where supported | Partial | Renderer uses size, brightness, contrast, saturation, and flips; apply/restart through UI remains. |
| 9 | Emergency stop safely halts virtual movement | Partial | PiSD zero-output path reaches the engine, which brakes; full Manual Drive STOP test remains. |
| 10 | Recording creates valid compatible synthetic datasets | Partial | Recorder output remains in isolated workspace and manifest metadata marks synthetic; end-to-end trainer import remains. |
| 11 | Injected faults exercise real PiSD error handling | Planned | No fault injection adapters yet. |
| 12 | Automated browser tests use actual PiSD interface | Planned | No Playwright suite or screenshot capture yet. |
| 13 | Emulator settings remain isolated | Implemented, unverified | Separate workspace root is passed to settings, model, and recording services; verify by live restart. |
| 14 | Existing PiSD functionality is preserved | Partial | Hooks default to `None`; ported onto current GitHub `main` PiSD 0.11.45 after reviewing notes 0.11.43–0.11.45. Full live PiSD regression remains unverified. |
| 15 | Tests cannot activate physical GPIO or motors | Implemented | Emulator app factory rejects hardware mode; adapter test confirms GPIO is not enabled. |
| 16 | Automated tests run without physical hardware | Implemented | `scripts/test_emulator.py` exercises engine and real PiSD service adapters on desktop. |
| 17 | Install and launch instructions match implementation | Implemented, unverified | Launcher path and arguments are in `README.md`; live launch needs installed PiSD dependencies. |

## Current implementation evidence

- `python -m compileall -q PiSD/pisd PiSD_Emulator` — passed in the implementation environment.
- `python PiSD_Emulator/scripts/test_emulator.py` — 13 tests passed.
- `python PiSD/PiSD.py --status-only` — expected to remain available without Flask; run after applying the patch.
- Flask and browser dependencies were not present here, so live app/API/UI and screenshot acceptance remains open.

## E04/E05 candidate reconciliation — 2026-11-28

Requirements 1–5, 9, 12–14 have subsequent scoped Linux browser evidence from #96/#102/#104 (including origin rejection, virtual drive/STOP, multi-context settings and restart). Do not infer physical or Windows live browser acceptance. Requirements 6, 10 and 11 have a new real-model/recording/camera-fault integration test candidate; replay from recording labels and image folders is implemented, open-loop. Exact CI pending; no complete milestone claim. Existing acceptance requirements unchanged.

### E04/E05 second checkpoint

Requirement 6 (real Keras service loop), 10 (recording labels and ZIP), 11 (camera capture fault/latch/rearm) passed scoped Linux software gate at a0ab6514. Actual AI page and trainer import, video and motor disconnect are implemented or test-covered in the new candidate pending exact CI. No full E04/E05 acceptance yet.

### Third checkpoint

Parent dd67c688: requirements 6/10/11/12 expanded software evidence: real AI browser, actual downloadable ZIP imported through existing trainer loader, video replay and motor disconnect tests passed. Independent artifact matched 12 rows/images and four screenshots. New model/API/GPIO/transport scenarios pending exact CI; no complete native trainer GUI, full network outage, hardware or cross-platform release acceptance.

### Fourth checkpoint

E05 scoped Linux service fault and browser transport evidence independently verified at c8da3455. New E02/E03 stopped-runtime custom track/lighting/markings/obstacle profiles, persistence and bounded request/metric history/export are implementation candidates pending exact CI. No physical, native trainer GUI or Windows live emulator acceptance.
