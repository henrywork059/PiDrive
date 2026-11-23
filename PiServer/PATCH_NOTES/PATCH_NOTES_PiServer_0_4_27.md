# PiServer 0_4_27 — R48 read-only startup and preflight panel

## Request
Implement roadmap **R48** using existing PiServer service status and camera diagnostic data: show service mode, camera, model, motor adapter, disk space, network, explicit simulation-versus-real labels and a reason/next step when a feature is unavailable. Opening/reloading preflight must not initiate GPIO, motor motion, camera startup, model load, network probes, settings save, or reset user data.

## Exact baseline and anti-rollback comparison
- New branch `update/piserver-0_4_27-r48-readonly-preflight` was created at the live head of **R47 draft PR #72**, `update/piserver-0_4_26-r47-request-tracing`, commit `7d61115eca28739c2527147116d312e26fb5a58e`. It is an **unmerged stacked draft**, not a reset to uploaded `PiDrive-main.zip` or main.
- Inspected actual launcher `PiServer/server.py`, current `piserver/app.py`, `services/camera_service.py`, `motor_service.py`, `model_service.py`, `control_service.py`, `web/templates/index.html` and existing `app.js`. Reviewed latest component notes and three predecessors **0_4_26 R47**, **0_4_25 R46**, **0_4_24 R45**, **0_4_23 R43**. Retain R47 sanitized API failures, R46 copy, R45 saved visual style, R43 polling, R35 STOP and R31 settings confirmation.
- Version line remains **0_4_x**, advanced from **0_4_26 → 0_4_27** in the existing `piserver/app.py` constant only.

## Root cause
PiServer exposes camera, model, motor, status and safety information, but operators must inspect separate panels or diagnostics to understand why AI/motor/preview is unavailable. A naive “test hardware” readiness feature would itself start/drive motors or mislabel a GPIO-capable/placeholder camera as confirmed safe physical hardware. The existing status panel and docking/resizable layout must not be redesigned to solve this.

## Files changed and exact behavior
1. **New** `PiServer/piserver/core/preflight.py`: a pure six-row formatter from existing read-only camera configuration, motor GPIO availability, active-model flag and existing safety latch. Uses only `shutil.disk_usage` for free/total disk bytes, with less-than-1-GiB or less-than-5% advisory and safe unknown on OSError. Returns fixed status labels `ready`, `attention`, `simulation`, `unknown`, actionable text, `read_only:true`, server timestamp. Never includes absolute path, exception text, config payload, credentials or runtime secrets. Network row says **only that this browser HTTP request reached PiServer**; it never claims internet reachability or invokes DNS/socket connect.
2. `PiServer/piserver/app.py`: add only **GET `/api/preflight`** using `camera_service.get_config()`, `motor_service.get_config()`, `model_service.get_active_name()`, `control_service.safety_status()` and the existing project directory. Does **not** instantiate services (normal app startup already owns them), modify safety, issue STOP/rearm, call camera.start, load a model, write config or initialize another GPIO driver. Advance `APP_VERSION`.
3. **New** `PiServer/piserver/web/static/preflight.js`: GET-only request once after normal DOM load and on user **Refresh checks**, safe textContent-only rendering with bounded rows, explicit simulation/attention and honest offline state. No polling loop, POST, global shortcut or motor/camera call.
4. `PiServer/piserver/web/templates/index.html`: add a **collapsed native `<details>`** under the existing Status dock, keeping all status metrics and E-Stop/camera/manual panels, original grid positions and saved docking layout. `role=status` with `aria-live=polite`; compact label and one Refresh. Versioned new script tag after existing `app.js`. No global stylesheet, icon-size or theme override.
5. **New** `PiServer/tests/test_preflight_r48.py`: **11** hardware-free unittest cases for six checks, mock-vs-real, placeholder, missing model, safety latch, disk success/error, immutability, network semantics and source-level no-actuator-route guard.
6. **New** `PiServer/tests/test_preflight_ui_r48.cjs`: **7** Node cases including async browser GET-only fetch, text-only DOM, refresh, unavailable response, simulation/attention rendering and template accessibility.
7. `PiServer/README.md`: operator preflight contract and exact test/release instructions.
8. `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_27.md`: this note.

## Verification actually performed
- **7/7 exact committed PiServer JS test callbacks passed** in an isolated V8 Node-compatible harness with fake DOM/fetch, using live GitHub source. Across PiServer, PiSD and both CustomDrive web apps **28/28 callbacks passed**; test scripts also parsed. **Native `node --test` was not run.**
- Performed direct static source-contract checks: all six read-only data fields present; new GET route and template reference present; new browser script parses; no motor, camera-start, model-load, filesystem-write or network-probe call in the formatter. These do not establish actual hardware readiness.
- **11 committed Python unittest cases were not executed** against this exact checked-out branch, nor was real Flask app boot, camera/motor hardware, screenshot or full PiServer suite. The standalone pure formatter is designed to be testable without Flask or Pi hardware; execute it before merge.
- Direct-parent GitHub compare must be completed and exact file/rollback evidence included in the draft PR.

## Known limits and acceptance/release gate
- GPIO **available** and camera backend **picamera2/opencv** mean adapter detected, not verified physical motor motion or a fresh frame. The camera may already have been initialized during the **normal main app startup**; the **preflight GET** never initializes it.
- Network row does not verify local router, Wi-Fi or internet; use PiBooter/network diagnostics for that. Disk threshold is advisory, not a write test or quota guarantee. A latched STOP remains latched. Model selected does not prove inference accuracy.
- Run `cd PiServer && python -m unittest discover -s tests -p 'test_preflight_r48.py' -v`, then `node --test PiServer/tests/test_preflight_ui_r48.cjs` from repo root and all old tests. On actual Pi check no-model/missing-camera/placeholder, hardware vs simulation, low disk, offline browser, current modal/focus/STOP and saved settings across restart. Verify preflight never activates motors or discards user settings.
- **Draft only: do not merge until predecessor PRs and real release tests are reviewed.**
