# PiSD 0.11.46 — PiSD Emulator integration

## Request summary

Add a local emulator that runs the actual PiSD interface with a virtual camera
and vehicle. Keep the normal PiSD runtime paths available and isolate emulator
settings, models, and recordings from the PiSD source tree.

## Baseline and rollback review

- Current GitHub `main` baseline: `14c57c990ff0f9bae2003e4e8aa552d17a4227c7`, with PiSD version `0.11.45`.
- Reviewed PiSD patch notes `0.11.43`, `0.11.44`, and `0.11.45` before porting the emulator hooks.
- The implementation retains current-main request tracing, access control, R35 setup accessibility, R36 responsive UI changes, AI model safety, recording safeguards, and motor command leases.
- This is a forward `0.11.x` patch; it does not promote a stable baseline.

## Cause / context

PiSD's existing simulation mode disables physical devices, but it does not
connect motor output to a moving vehicle or provide a camera view that follows
vehicle motion. The emulator adds those virtual devices through optional
adapters while leaving the PiSD app, camera pipeline, motor mapping, safety
checks, and UI as the runtime used by the simulation.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/services/recording_service.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_46.md`
- `PiSD_Emulator/` — launcher, control workspace, renderer, vehicle engine, tests, requirements, roadmap, and patch notes.
- `README.md`

## Exact behavior changed

- `create_app()` accepts optional virtual camera and motor adapters plus a
  separate runtime data root. Existing callers default to the current PiSD
  configuration and hardware/simulation behavior.
- Emulator mode rejects hardware-enabled startup before importing or
  constructing hardware services. Both emulator web servers bind to loopback.
- PiSD CameraService receives rendered frames from the emulator and continues
  through the normal JPEG publication pipeline.
- PiSD MotorService sends its mapped wheel outputs to the virtual vehicle and
  reports the adapter as `emulator`; normal motor behavior is unchanged when no
  output sink is supplied.
- Recording manifests identify emulator data as `synthetic_simulation` while
  trainer-facing labels keep their existing fields.
- PiSD version advances from `0.11.45` to `0.11.46`. Emulator data is stored in
  a separate workspace.

## Verification actually performed

Against the current-main source files plus the emulator integration:

```bash
python -m compileall -q PiSD/pisd PiSD_Emulator
python PiSD_Emulator/scripts/test_emulator.py
node --check PiSD_Emulator/web/assets/app.js
python PiSD/PiSD.py --status-only
```

All 13 emulator engine/service tests passed. Python compilation and JavaScript
syntax checks passed. PiSD status-only returned `PISD-OK-000` in basic
simulation mode.

## Known limits / next steps

Flask is not installed in this environment, so the live PiSD server, emulator
control workspace, browser rendering/interactions, and full PiSD regression
suite were not run. No physical Raspberry Pi checks were performed. Install
`PiSD/requirements.txt`, launch `PiSD_Emulator/run_emulator.py`, and complete the
browser smoke checks in `PiSD/docs/TEST_PLAN.md` before treating the live
integration as browser-verified.

## Revision B — configuration-path regression repair (UI2 blocker)

Exact E01 parent 42674e49c94f86b73df06e6727a365edd7be5e16: Linux 46025487935 failed PiSD F7 recovery warning and Manual/Settings native browser speed readback (expected 0.43, actual 0.80); remaining three Linux jobs and Windows 46025488000 passed. Source inspection confirms the new data-root path bypassed RUNTIME_SETTINGS_PATH for ordinary calls. Restore the existing path when runtime_root is omitted, retain explicit workspace isolation, and add an F7 workspace read/save regression. No test expectations, camera/motor logic, defaults, or version changed. Reviewed 0.11.45/44/43 notes; exact corrected CI pending. Local Flask/Qt unavailable; no local browser or physical test claimed. Performance #88/#89 also touch PiSD 0.11.46; this repair is confined to E01 and is not authorization to merge either branch or promote stable.
