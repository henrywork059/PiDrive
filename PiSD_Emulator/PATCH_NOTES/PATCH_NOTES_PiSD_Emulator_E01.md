# PiSD Emulator E01 Patch Notes

## Request summary

Begin an operational PiSD Emulator inside the PiDrive monorepo. The first delivery should establish the emulator application, virtual hardware services, driving/camera feedback, actual PiSD UI integration, and a requirement tracker.

## Cause / context

PiSD's existing basic simulation safely disables physical hardware, but it uses placeholder camera imagery and does not move a vehicle from PiSD motor outputs. That is insufficient for checking Manual Drive, AI, camera processing, and recording as a closed loop.

## Files added or changed

- `PiSD_Emulator/run_emulator.py`
- `PiSD_Emulator/pisd_emulator/engine.py`
- `PiSD_Emulator/pisd_emulator/renderer.py`
- `PiSD_Emulator/pisd_emulator/runtime.py`
- `PiSD_Emulator/pisd_emulator/control_app.py`
- `PiSD_Emulator/web/index.html`
- `PiSD_Emulator/web/assets/app.css`
- `PiSD_Emulator/web/assets/app.js`
- `PiSD_Emulator/scripts/test_emulator.py`
- `PiSD_Emulator/README.md`
- `PiSD_Emulator/ROADMAP.md`
- `PiSD_Emulator/REQUIREMENTS.md`
- `PiSD_Emulator/PATCH_NOTES/PATCH_NOTES_PiSD_Emulator_E01.md`
- PiSD 0.11.46 app, camera, motor, and recording adapter hooks and documentation.

## Exact behavior changed

- The emulator runs the actual PiSD app factory with a virtual camera provider and virtual motor-output sink.
- The virtual vehicle uses PiSD's mapped outputs at a deterministic fixed timestep and produces a perspective road image for PiSD CameraService.
- The browser workspace embeds the actual PiSD Manual Drive page, shows the virtual vehicle and GPIO/PWM outputs, and controls the local PiSD runtime.
- Emulator hardware mode is rejected; both servers bind to localhost; runtime settings, models, and recordings go to the emulator workspace.
- Synthetic recordings keep PiSD's existing trainer-facing label fields and mark their manifest source.

## Verification performed

- `python -m compileall -q PiSD PiSD_Emulator` — passed.
- `python PiSD_Emulator/scripts/test_emulator.py` — 13 checks passed.
- `node --check PiSD_Emulator/web/assets/app.js` — passed.
- `python PiSD/PiSD.py --status-only` — returned `PISD-OK-000` in basic simulation mode.

The emulator was ported to the current GitHub `main` tree at PiSD 0.11.45, and the PiSD integration is versioned 0.11.46. The current-main PiSD notes 0.11.43, 0.11.44, and 0.11.45 were reviewed before porting. The test harness compares against the running PiSD version instead of a hard-coded 0.11.1 value. The environment did not have Flask installed. Live HTTP startup, browser rendering and interaction, screenshots, full PiSD standard validation, and physical Raspberry Pi checks were not performed.

## Known limits / next steps

See `PiSD_Emulator/ROADMAP.md` and `PiSD_Emulator/REQUIREMENTS.md`. The immediate next step is a live browser smoke test with PiSD requirements installed, followed by Playwright coverage of the actual PiSD pages and controls.
