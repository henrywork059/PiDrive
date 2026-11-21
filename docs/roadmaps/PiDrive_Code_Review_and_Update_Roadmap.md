# PiDrive Code Review and Update Roadmap

**Review date:** 2026-11-21  
**Scope:** Read-only static inspection and selected local validation of uploaded archives  
**Sources:** `PiDrive-main.zip`, `PiSD_0_11_0.zip`, `piTrainer_0_11_0.zip`  
**Status:** Recommendations only; no PiDrive source files have been patched.

## 1. Review approach and baselines

PiDrive is an active monorepo, not a single application. The review inspected component trees, launchers, selected runtime/services, representative UI and training integrations, dependency manifests, and the latest patch note plus the preceding three notes where available.

- **PiSD:** prefer `PiSD_0_11_0.zip` to `PiDrive-main.zip/PiSD/` (35 shared files differ; 15 more files in the newer archive, excluding caches). Preserve all accepted 0.10.x and 0.11.0 fixes, especially recording frame naming, AI output controls, keyboard shortcuts and UI layout.
- **piTrainer:** prefer `piTrainer_0_11_0.zip` to `PiDrive-main.zip/piTrainer/` (52 shared files differ; 43 more files in the newer archive, excluding caches). Preserve V11 functionality, non-overwriting model exports, Data sorting, selection persistence, dock layout and validation behavior.
- **PiServer:** repository copy is at `APP_VERSION = "0_4_10"`; stable baseline is 0_4_0, with forward patches in 0_4_x. The latest patches correct camera AWB defaults and snapshot behavior; do not regress these.
- **PiBooter:** repository copy contains patches through 0_1_1; keep independent from PiServer.
- **CustomTrainer:** repository copy contains patches through 0_2_11; preserve current Marking layout, quick deploy and exported-model validation.
- **CustomDrive:** repository copy contains Mission 1 patch notes and code through 0_5_16. Preserve its actual live/simulation functionality, pickup/drop-off trigger semantics and arm/motor UI.
- **Legacy piCar:** not present as a top-level folder in this specific archive; do not create or modify it speculatively.

The root `README.md` is older than some component code: it describes a CustomDrive 0_4_15 marker even though `custom_drive/mission1_session_app.py` is 0_5_16.

## 2. Findings, evidence, impact, recommended changes

### F1 — Critical: non-finite control inputs can become full-scale commands (PiServer)

**Evidence:** `PiServer/piserver/services/control_service.py` has a local `_parse_float()` accepting `float("nan")` and `float("inf")` without `math.isfinite()`. Its `_clamp()` uses `max(minimum, min(maximum, value))`. Direct local reproduction: the string `"nan"` in the [-1, 1] clamp becomes +1; infinity also becomes +1. The existing `piserver/core/value_utils.py` already implements `parse_finite_float`.

**Action:** Remove duplicated unsafe parsing in the control service, use finite-value validation for all motor/runtime inputs, and reject invalid control requests or zero motion for safety-critical invalid data. Audit other API-to-motor paths for non-finite inputs. Add tests for `NaN`, `Infinity`, `-Infinity`, strings, nulls, and malformed JSON. Preserve existing finite-value clamping behavior.

**Acceptance:** No non-finite input can result in a nonzero motor command. API behavior is explicit and covered by regression tests.

### F2 — Critical: motor commands can persist without fresh operator updates

**Evidence:** `PiServer/piserver/services/control_service.py` stores `manual_steering` and `manual_throttle` and applies them every control-loop tick, with no command timestamp/expiration check found. `PiSD/pisd/app.py` applies manual output directly in `/api/control/manual`. PiSD browser code sends stops on pointer release/page hide, but lost requests and process crashes can defeat browser-only stopping.

**Action:** Implement a monotonic server-side command lease/watchdog and zero-output fail-safe, ideally at the motor arbitration layer, with separately specified manual/AI semantics. Apply to PiServer first, then PiSD and CustomDrive's live driving paths. Require explicit rearming when appropriate; preserve the user-facing global Space STOP. Add deterministic fake-clock tests for timeout, network dropout, repeated commands, algorithm changes, shutdown, and recovery.

**Acceptance:** Stale operator input leads to a motor stop even if no browser STOP packet arrives; no spontaneous restart after a stop; simulated and hardware adapters share the same policy.

### F3 — High: LAN motor-control endpoints lack observable access controls

**Evidence:** `PiServer/server.py` runs Flask on `0.0.0.0:5000`; `piserver/app.py` registers mutating routes without visible authentication middleware. PiSD has LAN-bind instructions and similarly exposes motor-control and settings routes. CustomDrive Mission 1 defaults to `0.0.0.0`.

**Action:** Offer safe loopback defaults for local development, opt-in LAN exposure, operator-token/session authentication for command and settings routes, and protection from unintended cross-origin/CSRF requests. Keep emergency STOP accessible to authorized operators even during degraded state. Document network scope and avoid placing secrets in committed runtime JSON.

**Acceptance:** Unauthorized requests cannot move motors or change hardware settings; authorized local/LAN workflows still work; safe stop remains reliable.

### F4 — High: PiSD AI verification does not run on shipped V11 baseline

**Evidence:** `PiSD_0_11_0/PiSD/scripts/test_ai_mode_page.py` and `scripts/run_standard_validation.py` import `pisd.services.ai_correction` and `pisd.services.ai_safety`; neither file is present in either archive. The actual runtime has correction and safety methods embedded in `pisd/services/ai_drive_service.py`. Direct local runs of both test commands fail at import before any assertions. Recent PiSD patch notes claim those helpers were preserved.

**Action:** Reconcile runtime versus test expectations. Extract correct helpers and use them from the production service, or update tests to target the actual production methods; avoid duplicate safety logic. Add a preflight import check and ensure standard validation genuinely runs rather than only compiling.

**Acceptance:** AI Mode test and standard validation pass in the simulation environment; unit tests cover additive manual correction, steering limits, fixed-throttle semantics and fail-safe motor behavior.

### F5 — High: PiSD AI command timeout setting is apparently inert

**Evidence:** `PiSD/pisd/core/settings_manager.py` and `pisd/services/ai_drive_service.py` normalize/store `ai_mode.command_timeout_s`, but inspection of the service shows no timeout enforcement in its `_run_loop()`. The separate `manual_correction_timeout_s` is used; they should not be conflated.

**Action:** Define exactly what `command_timeout_s` guards (e.g., stale camera frame, inference cycle, motor output or client lease), implement and document it, and add simulated clock/stalled-inference tests. If the setting is obsolete, remove it only via a backward-compatible, explicitly documented migration.

**Acceptance:** Changing the setting visibly changes the intended timeout behavior, verified by tests and status diagnostics.

### F6 — High: test coverage is uneven across components

**Evidence:** PiServer has eight `tests/test_*.py` modules and passes 35 `unittest` cases in this environment. PiSD has a significant scripts-based test suite, but the standard runner is currently blocked by F4. No `test_*.py` modules were found within the uploaded piTrainer, CustomTrainer, PiBooter and CustomDrive component roots; a few demos/stage tests are present in CustomDrive, but they are not a conventional isolated regression suite.

**Action:** Introduce lightweight, hardware-free tests around recording import, label edits, training/export path selection, YOLO deployment command construction, Mission 1 state transitions/coordinate conversion, PiBooter network transitions and settings migration. Add CI workflows with a component matrix and explicit optional dependencies. Do not attempt real TensorFlow training or Pi GPIO access in generic CI.

**Acceptance:** Every active component has runnable deterministic unit/contract tests, and a change that breaks a component's critical accepted behavior fails CI.

### F7 — Medium/high: config errors can silently become defaults

**Evidence:** `PiServer/piserver/core/config_store.py::load_raw()` returns `{}` on any parse exception, and `CustomDrive/custom_drive/run_settings.py::load_run_settings()` does likewise. A later save can then replace the operator's original broken-but-recoverable file with defaults. PiSD emits an error on parse failure but similarly reverts in memory to defaults.

**Action:** On corruption, log a clear visible warning with the original file path, back up malformed files before any write, preserve raw settings for recovery, normalize only keys known to require bounds, and add restart/round-trip tests. Do not change or reset packaged user configuration in a patch.

**Acceptance:** Invalid JSON cannot be silently overwritten on subsequent save; a useful diagnostic and a recovery copy remain available.

### F8 — Medium: large modules are slowing safe changes

**Evidence:** `CustomDrive/custom_drive/mission1_session_app.py` is ~1,914 lines; `CustomTrainer/custom_trainer/ui/pages/marking_page.py` ~1,333; `PiBooter/pibooter/app.py` ~930; PiSD's camera, recording and AI services approach 900–1,200 lines. This is a maintainability concern rather than proof of incorrect behavior.

**Action:** After safety and tests, extract pure logic into modules with stable interfaces: Mission 1 state-transition functions, frame-coordinate normalization, model output decoding, arm pose sequencing, session persistence; similarly separate CustomTrainer UI actions and backend services. Avoid broad folder restructures or breaking import paths. Use characterization tests before extraction.

**Acceptance:** Identical externally visible behavior, unchanged launch commands and config paths, and targeted tests for each extracted unit.

### F9 — Medium: dependency declarations and release packaging need improvement

**Evidence:** `CustomDrive/requirements.txt` describes itself as a standard-library draft but the live code uses Flask and optional camera/vision/TFLite/PiServer services. `PiDrive-main.zip` includes 77 `.pyc` files, and `piTrainer_0_11_0.zip` includes 47 `.pyc` files. No `.github/workflows` or `.gitignore` was present in these provided archives. The root README has a stale CustomDrive version marker.

**Action:** Specify documented minimal, desktop, Pi hardware and development dependency groups; consider constraints/lock files for supported environments. Exclude caches, generated output and user-local config from future distributions without deleting user data. Add packaging checks for expected version, file list, launch paths and patch-note inclusion. Keep root README synchronized to actual code.

**Acceptance:** A clean documented installation can launch the intended mode; release artifacts have no unnecessary caches and no unrequested user data; version markers agree.

### F10 — Medium: define an end-to-end PiSD → piTrainer → PiSD contract

**Evidence:** `PiSD/pisd/services/recording_service.py` writes `labels.jsonl`, `records.jsonl`, `manifest.json`, frame identities and overlay settings. `piTrainer/piTrainer/services/data/record_loader_service.py` explicitly prioritizes `labels.jsonl`, normalizes steering/throttle, and supports multiple historical field names. This integration deserves release-level compatibility checks.

**Action:** Add small committed synthetic fixtures (not real user recordings) for current plus legacy schemas; exercise piTrainer ingestion, per-frame label edits, hidden-frame exclusion, flipped steering, non-overwriting exports and TFLite output shape/ordering. Verify exported model acceptance in PiSD using metadata/model stubs rather than requiring a live Pi for every CI run.

**Acceptance:** Contract tests prevent incompatible recording or model-output changes across component releases.

## 3. Recommended execution sequence

### Phase 0 — Repository synchronization and reproducible verification
1. Create a non-destructive baseline snapshot/checksum manifest for each current component.
2. Treat the newer PiSD and piTrainer archives as authoritative for those components. Do not copy old monorepo files over them.
3. Repair PiSD F4 before trusting its aggregate validation results.
4. Add a basic CI/check script that compiles source, verifies imports, checks JS syntax and runs tests where dependencies exist.
5. Record current known failures separately from new regressions.

### Phase 1 — Physical safety and interface hardening (highest payoff)
1. **PiServer:** finite-value validation and tests (F1).
2. **PiServer:** watchdog/command lease plus stale-data and model-unavailable fail-safe (F2).
3. **PiSD:** enforce actual manual/AI command timeout semantics (F2, F5), preserving one AI safety confirmation and global Space STOP.
4. **PiServer/PiSD/CustomDrive:** LAN access policy and authorized control (F3).
5. Verify motor direction, reverse behavior, camera AWB, saved max throttle, e-stop and restart conditions in simulation, then on Raspberry Pi with wheels safely lifted.

### Phase 2 — Data integrity and tests
1. Config corruption recovery and migration/round-trip tests for PiServer, PiSD and CustomDrive (F7).
2. Cross-component recording/model contract fixtures and tests (F10).
3. piTrainer unit tests for Data filtering/review, mirrored steering, non-overwriting save/export, and Validation→Data return state.
4. CustomTrainer tests for label parsing, Marking quick-deploy and exported model validation.
5. CustomDrive simulation mission-state tests, especially grip/drop-off trigger coordinate conversion and arm stop/release ordering.
6. PiBooter tests using mocked NetworkManager responses and network recovery cases.

### Phase 3 — Refactoring and release engineering
1. Extract pure logic from large modules only where tests characterize existing behavior (F8).
2. Standardize logging, typed configuration validation and actionable error statuses.
3. Align per-component requirements and supported Python version matrices (F9).
4. Add CI, packaging checks, `.gitignore`, and truthful root/component docs (F9).
5. Package component-specific forward patches with only changed/new files and detailed patch notes; compare to the previous three patch notes before shipping.

## 4. First proposed patch package (recommended)

**Scope:** PiServer safety-only patch on the existing 0_4_x line, not a repo-wide rewrite.

**Minimal likely files:**
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/core/value_utils.py` (only if a shared helper change is needed)
- `PiServer/tests/test_control_service.py`
- `PiServer/PATCH_NOTES/<next-accepted-0_4_x-file>.md`

**Work:** fix non-finite command parsing, add a manual command lease/watchdog, define e-stop recovery behavior, add regression cases, and verify no rollback of snapshot/camera AWB improvements. Confirm the next version number from the accepted patch lineage before naming the zip. Keep `PiServer/config/runtime.json` untouched.

**Definition of done:** bad numeric inputs never produce motor motion; stale manual commands stop motors without browser intervention; all existing PiServer tests and added tests pass; all launch files remain unchanged; hardware-only checks are disclosed accurately.

**Second patch:** PiSD validation reconciliation, followed by its independently tested server-side motor watchdog. Do not combine with unrelated UI changes.

## 5. Verification actually performed in this review

| Check | Result |
|---|---|
| Full Python syntax compilation, all three source archives | Pass |
| PiServer `python -m unittest discover -s tests -q` | 35 tests passed |
| PiSD V11 `python PiSD.py --status-only` (simulation mode) | Passed, `PISD-OK-000` |
| PiSD V11 `scripts/test_ai_drive_service.py` | Passed |
| PiSD V11 `scripts/test_settings_persistence.py` | Passed |
| PiSD V11 `scripts/test_recording_service.py` | Passed |
| PiSD V11 `scripts/test_ai_mode_page.py --static-only` | Failed: missing `pisd.services.ai_correction` |
| PiSD V11 `scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui` | Failed: same missing import |
| Syntax check, 14 PiSD JS files via `node --check` | 14 passed |
| Direct PiServer non-finite parser reproduction | `"nan"` clamps to +1 in range [-1, 1] |

### Not performed / limitations
- No Raspberry Pi, GPIO, camera or physical motor testing.
- No live Flask API execution here (Flask not installed in this review environment).
- No PySide6 GUI, TensorFlow training/export, Ultralytics model run or TFLite inference with a real model (these dependencies are unavailable here).
- No Git history or remote repository branch comparisons; review based on the three provided archives.
- The findings arise from selected critical-code inspection, tree analysis and lightweight tests, **not** a claim that every function was audited.

## 6. Explicit anti-rollback guardrails

- **PiServer:** preserve recent camera AWB off default, snapshot fixes, motor direction and saved settings.
- **PiSD:** preserve the 0_11_0 one-confirmation AI UI, shortened text, recording frame naming restored in 0_10_10, AI correction semantics, preview controls above images, Space STOP and camera color settings.
- **piTrainer:** preserve V11 train/validate/export navigation, Data default sorting, session selection, controls, mirrored steering, non-overwriting model saves and panel layout.
- **CustomTrainer:** preserve 0_2_11 narrower Marking tools, quick-deploy model selection and Export Validate tab.
- **CustomDrive:** preserve 0_5_16 pickup/drop-off Y ratios, backward-after-drop-off setting, prior model/arm simulation and motor calibration behavior.
- **PiBooter:** remain a standalone component; do not ship unrelated PiServer files in its patch zip.

**Recommended next action:** Start with a narrowly scoped PiServer safety patch, then repair PiSD AI validation and add its motor timeout protections. This sequence removes the most important risk before any larger refactor.
