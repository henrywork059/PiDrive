# PiSD 0.11.21 — R48 read-only startup preflight

## Request and acceptance
Implement roadmap **R48** from live PiSD service status and the **non-loading** AI runtime diagnostics rather than a motor/camera “test.” Provide an operator-facing passive six-check summary (service mode, camera, model/runtime, GPIO adapter and safety, disk space, HTTP/network) with actionable disabled reasons, real/simulation distinction, and **no motor/camera/AI initialization or loss of persistent settings from preflight**.

## Exact baseline, launcher and rollback review
- Direct parent: **R47 draft PR #73**, branch `update/pisd-r47-request-tracing`, head commit `a6378956fdff8d94371eb2644a8f47220dbad5a3`. R48 branch `update/pisd-r48-readonly-preflight` is an additive forward stack; no merge or zip overwrite.
- Inspected real `PiSD/PiSD.py` launcher, `pisd/app.py`, `core/errors.py`, `services/camera_service.py`, `services/motor_service.py`, `services/ai_drive_service.py`, and `web/templates/front_page.html`. Reviewed latest component notes **R47 0.11.20**, **R46 0.11.19**, **R43 0.11.18**, **R36 0.11.17**; preserve R35 Space STOP, R32 hardware readiness and R31 settings persistence.
- Honor the existing `0.11.x` patch line: **`pisd/__init__.py` 0.11.20 → 0.11.21**, for normal asset cache versioning. No change to `config/defaults.json`, `config/runtime_settings.json`, model/recordings directories or runtime mode passed to `PiSD.py`.

## Root cause
A model can be uploaded while the correct Python TFLite runtime is absent, a Pi boot can request hardware yet fall back to simulated GPIO or camera frames, and a camera may be stopped with a safety latch. These conditions appear in separate, often lengthy status/debug views but are not summarized in a safe preflight. A new "diagnose hardware" route must not call camera.start(), motor.stop()/update(), model load/infer, a network scanner, or settings reset just to report readiness.

## Files changed and actual behavior
1. **New** `PiSD/pisd/core/preflight.py`: pure six-row builder from existing `camera_service.status()`, `motor_service.status()`, `ai_drive_service.status()` and `ai_drive_service.safety_status()`. Explicitly compares hardware **requested** against actual camera backend (`picamera2` + running) and actual `hardware_enabled` GPIO. Reports simulation, unavailable camera and latched AI-camera-fault safety without changing them. For AI model, uses already available `model_loaded`, `model_ready` and `runtime_support.tflite` (existing `runtime_diagnostics()` import availability) to distinguish missing TFLite runtime from missing/deactivated model and suggest installing tflite-runtime. Does not invoke `check_ai_runtime.py` or instantiate an inference interpreter. `shutil.disk_usage(PROJECT_ROOT)` is read-only; warn at less than 1 GiB or 5% free and suppress exception paths. Network means **HTTP request to this PiSD process only**, never internet verification. All rows have title/state/detail/next_step; result has `ok:true`, `read_only:true`, timestamp.
2. `PiSD/pisd/app.py`: **GET `/api/preflight`** using existing services and their read-only getters; no POST handler, GPIO/camera init, AI model load, network probe or settings save.
3. `PiSD/pisd/__init__.py`: bump patch version **0.11.21**.
4. **New** `PiSD/pisd/web/static/js/preflight.js`: one GET on front page load and on deliberate Refresh, bounded text-only list, simulation vs attention, honest offline failure. No status poll loop, model/motor/camera action or localStorage writes.
5. `PiSD/pisd/web/templates/front_page.html`: collapsed native `<details>` preflight within existing quick actions, next to Refresh status and STOP motors, without replacing the status console/workspace cards or relocating camera/drive panels. Accessible status with aria-live. Versioned static script.
6. **New** `PiSD/scripts/test_preflight_r48.py`: **12** hardware-free Python stdlib tests for fallback vs real, TFLite present/missing, camera off/simulated, safety latch, disk/permission errors, snapshot immutability and GET-only app wiring.
7. **New** `PiSD/scripts/test_preflight_ui_r48.cjs`: **7** Node browser tests for GET-only network behavior, safe text rendering, simulation and unavailable states, explicit Refresh and accessibility.
8. `PiSD/README.md`: test/release directions and network-status limitation.
9. `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R48.md`: this note.

## Verification actually performed
- **7/7 exact committed PiSD preflight browser test callbacks passed** against the exact GitHub branch contents in a V8-compatible fake DOM/fetch runner. Combined PiServer/PiSD/CustomDrive GUI/Mission browser preflight suites passed **28/28**. This is **not native `node --test`** or a real browser.
- Executed live source checks confirming six named states, pure read-only formatter without motor/camera/settings writes, GET route, template/script wiring and successful JS parse.
- **12 new Python tests were committed but not run** on a checkout of the exact PR; no Raspberry Pi camera, real motor, network interface, disk quota or complete Python integration tests were performed.
- **Direct-parent GitHub compare completed** against R47 PR #73: **10 commits ahead, 0 behind; 9 component-local files changed (5 new, 4 modified); 0 deletions; 0 cross-component paths**. Existing motor/camera/AI/recording services, R47 error redaction, R43 hidden MJPEG, R35 STOP, R36 styling and user runtime/config values were not modified.

## Known limits / release gate
- A running Picamera2 backend is not proof of fresh frames. A GPIO motor adapter being initialized is not a physical movement test, and read-only preflight never arms or rearms motors. TFLite import-spec availability is not a completed model inference. This does not replace an operator-controlled guarded test.
- PiBooter is the source for actual Wi-Fi/router status. The preflight only establishes HTTP reachability *from the current page*; it never scans/joins networks, pings, or claims internet connectivity.
- Run `cd PiSD && python -m unittest discover -s scripts -p 'test_preflight_r48.py' -v`, then `node --test PiSD/scripts/test_preflight_ui_r48.cjs` at repo root, and full PiSD service regression. On a real Pi test mock vs `--hardware`, Picamera2 off/on, missing model/TFLite interpreter, low disk, camera-fault latch/rearm, original STOP and R43 hidden-tab MJPEG. Confirm NO motion, AI model loading or loss of `runtime_settings.json` from preflight GET.
- Draft only; R47/R46/R43 and earlier accepted patches remain dependencies. Never merge independently.
