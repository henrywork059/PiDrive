# PiDrive: Expanded Update Roadmap (Addendum)

**Date:** 2026-11-22  
**Source baselines:** `PiDrive-main.zip`; `PiSD_0_11_0.zip` for PiSD; `piTrainer_0_11_0.zip` for piTrainer.  
**Read-only scope:** additional static code inspection and isolated disposable-data reproductions. This document supplements, rather than replaces, `PiDrive_Code_Review_and_Update_Roadmap.md`. **No production source files were changed.**

## Why this addendum

The first review addressed control safety, LAN access, PiSD's broken AI test import, command timeout semantics, config corruption, test coverage, and code modularity (F1–F10). This addendum identifies more specific defects and improvements to data science correctness, model compatibility, deployment security, recording durability, autonomous control, and diagnostics. New items use identifiers U11–U29 to avoid conflicting with the original review.

## Newly identified issues and proposed changes

### U11 — P0: Prevent preprocessing/validation contamination (piTrainer)

**Files:** `piTrainer/piTrainer/services/preprocess/preprocess_service.py`; `piTrainer/piTrainer/services/train/split_service.py`; `piTrainer/piTrainer/pages/train_page.py`; tests to add.

**Evidence:** preprocessing builds mirror, color and turn-boost copies with `source_frame_id`. Train page splits the resulting expanded table; `TrainConfig.split_mode` defaults to `Random rows`. Consequently, transformed copies of an original image may be assigned to opposite subsets. In a disposable 8-source/16-row example, the actual `split_by_rows(..., 0.2, 42)` placed `frame-3` into both training and validation (1/3 validation rows in this example represented a source also in training).

**Design:** split on a stable source identity `(session, source_frame_id or original frame_id)` before creating training-only augmentations, or make group-aware random splitting the default when synthetic rows exist. Keep the existing session and sequential options and the explicitly accepted horizontal-flip steering inversion. Show counts of unique original frames, synthetic variants and overlap. Reject any train/validation intersection at the source group level. For a single source/group, show 'no independent validation set' instead of pretending to validate.

**Tests:** 100% of related variants stay together; no source image appears in both sets; split deterministic for a seed; hidden rows remain excluded; train/validation counts sensible for tiny data.

### U12 — P1: Read actual model input shape instead of resizing to a constant (PiServer)

**Files:** `PiServer/piserver/services/model_service.py`; `PiServer/tests/test_model_service.py`; model metadata/test fixtures.

**Evidence:** `MODEL_INPUT_WIDTH = 200`, `MODEL_INPUT_HEIGHT = 112` are hard-coded in PiServer `_prepare_input`. piTrainer defaults to image width 160, height 120 and builds CNN inputs with those dimensions.

**Design:** inspect the loaded TFLite input tensor `(batch,height,width,channels)`, validate it and preprocess to the interpreter's expected shape, dtype and quantization. Check output dimensions/meaning; return actionable load-time errors instead of repeated silent inference failures. Preserve support for older 200x112 models. This does not imply every trainer model currently targets PiServer; the goal is to establish compatibility rather than assume it.

**Tests:** load-time rejection for invalid shapes; successful simulated input for 160x120 and 200x112; RGB conversion, float and quantized tensors; output interpretation and non-finite guarding.

### U13 — P1: Treat the control API as a transaction (PiServer)

**Files:** `PiServer/piserver/app.py`; `PiServer/piserver/services/control_service.py`; API tests to add.

**Evidence:** `/api/control` calls `set_manual_controls()` and `set_runtime_parameters()` before attempting `select_algorithm()`. An unknown algorithm can trigger HTTP 400 after other state has been changed.

**Design:** parse/validate all proposed fields (including booleans, numeric types and algorithm choice) without side effects; apply the accepted command as one controller-state transaction under its lock. A partially invalid request leaves the previous state unchanged. Add a stable JSON error shape and tests around rejection, overlapping requests, and valid backward-compatible inputs.

**Tests:** invalid algorithm + otherwise valid throttle changes nothing; invalid numeric fields change nothing; valid multi-field command commits together.

### U14 — P1: Exclusive physical hardware ownership (PiServer/CustomDrive)

**Files:** `CustomDrive/custom_drive/live_runtime.py`; `CustomDrive/custom_drive/piserver_integration.py`; `PiServer/piserver/services/camera_service.py`; `PiServer/piserver/services/motor_service.py`; adapters/coordination tests.

**Evidence:** `LiveMissionRuntime` directly instantiates `CameraService()` and `MotorService()` from PiServer, while PiServer's `create_app()` also initializes those services. Running both may contend for camera/motor resources. This is a concurrency risk, not a claim that two processes have been observed colliding on hardware.

**Design:** define a single hardware owner per physical Pi. Prefer a narrow authorized control service/interface for CustomDrive when PiServer is the owner; allow standalone exclusive-owner mode only when PiServer is inactive. Add process-bound ownership diagnostics, explicit handover, and hardware-safe stop on handover failure. Do not reorganize the monorepo.

**Tests:** two simulated owners cannot drive at once; process crash expires lease; owner handover starts from stop and requires rearm.

### U15 — P1: Prevent same-second preprocessing output overwrite (piTrainer)

**File:** `piTrainer/piTrainer/services/preprocess/preprocess_service.py`.

**Evidence, reproduced:** `save_preprocessed_dataset()` uses folder `preprocessed_YYYYMMDD_HHMMSS`, then `ensure_dir(...)`. Two calls within one second returned the same folder and the second call overwrote `preprocessed_records.csv`, `preprocessed_records.jsonl` and `preprocess_recipe.json` from the first call. Reproduced safely in a temporary directory with two small dataframes.

**Design:** generate collision-resistant run directories (e.g. timestamp with microseconds plus suffix, or exclusive `mkdir` with incrementing counter) and stage export files before atomic publication. Keep existing folder names readable and existing files untouched.

**Tests:** two back-to-back saves always have different destinations, both remain readable, interrupted save does not replace a previous complete run.

### U16 — P1: Stop PiBooter destroying malformed configuration on load

**File:** `PiBooter/pibooter/config.py`.

**Evidence, reproduced:** `ConfigStore.load()` catches JSON syntax failures, builds defaults, then unconditionally writes those defaults to `self.path`. A malformed input was overwritten and no backup created in a temporary-directory test.

**Design:** separate read/normalize from write; never overwrite a malformed file automatically. Surface a warning, retain original bytes, allow user-approved backup-and-repair, and use atomic replace on successful saves. Retain unknown user keys and preserve `startup_wait_s`/auto-exit/status behavior.

**Tests:** corrupt config remains intact; backup exists before explicit recovery; unknown settings round-trip; atomic save failure keeps old file.

### U17 — P1: Make trainer label-file edits crash-safe (piTrainer)

**File:** `piTrainer/piTrainer/services/data/edit_service.py`.

**Evidence:** `_write_jsonl_entries()` directly opens a labels file with `'w'` and rewrites lines in place. A crash or storage error mid-write can truncate the session's label source. Its cache also retains full parsed entries for up to eight JSONL files.

**Design:** write to a unique same-directory temporary file, flush/fsync when appropriate, validate the file, then `os.replace`. Keep a recovery copy for user-edited labels and invalidate the in-memory cache after committing. Provide a clear conflict message if source file was externally modified after loading.

**Tests:** fault-injected write failure preserves old contents; successful updates change the intended frame only; cache returns newly committed labels; recoverable edits retain session selection/navigation.

### U18 — P1: Improve dataset partitioning and YOLO label validation (CustomTrainer)

**Files:** `CustomTrainer/custom_trainer/services/dataset_service.py`; `CustomTrainer/custom_trainer/services/yolo_io.py`.

**Evidence:** `_split_image_paths()` partitions sorted image paths periodically, not by capture session. For one image it deliberately returns that image for both train and val. YOLO parser clamps center/width/height separately and skips malformed lines, but does not report every partly invalid annotation or whether the resulting box extends past image bounds.

**Design:** offer group-by-session or sequence-block splits, warn for tiny datasets without a real holdout, and validate complete normalized box extents, class IDs, finite numbers and degenerate boxes. Produce a per-session data-quality summary before launching Ultralytics. Preserve the existing Marking quick-deploy and Export Validate page.

**Tests:** no cross-set frame group leakage; singleton explicit no-valid-holdout condition; invalid geometries rejected or safely normalized with a logged reason; class mapping consistent.

### U19 — P1: Secure PiBooter setup mode (PiBooter)

**Files:** `PiBooter/pibooter/config.py`; `PiBooter/pibooter/app.py`; `PiBooter/pibooter/network.py`.

**Evidence:** packaged defaults include a common hotspot password `pibooter1234`, `server.host=0.0.0.0`, HTTP port 80, and `allow_open_wifi=True`. This is a provisioning-security risk; exact deployed settings may differ.

**Design:** generate a per-device setup credential (without resetting an existing user credential), display it using a safe provisioning path, limit privileged network mutations to authorized clients, disable connecting to unsecured networks by default for new installs, and guard/expire setup sessions. Preserve the accepted short startup/auto-exit behavior.

**Tests:** existing credentials preserved; credentials not logged; unauthenticated config/network mutations denied; setup auto-exit still works.

### U20 — P1: Recover partially written recording sessions (PiSD)

**Files:** `PiSD/pisd/services/recording_service.py`; `PiSD/scripts/test_recording_service.py`.

**Evidence:** each frame is saved as JPEG, then appended independently to `records.jsonl` and `labels.jsonl`, and manifests are separately written. An interruption between these operations could leave frames without labels or unequal record/label counts. This is a fault-model risk; no data loss was reproduced.

**Design:** at session open, scan and report incomplete tail records, reconcile by stable source frame identity, provide non-destructive recovery, and preserve the original recording files for audit. Consider append batching only if bounded and always flush on clean stop. Retain current frame ID and two-JSONL contracts.

**Tests:** interrupted writes at each step; idempotent recovery; no duplicate labels or destructive automatic pruning; piTrainer can load recovered sessions.

### U21 — P1: Reject stale camera frames for autonomous motion (PiServer/CustomDrive/PiSD)

**Files:** `PiServer/piserver/services/control_service.py`; `PiServer/piserver/services/camera_service.py`; `CustomDrive/custom_drive/live_runtime.py`; `CustomDrive/custom_drive/mission1_session_app.py`; `PiSD/pisd/services/ai_drive_service.py`.

**Evidence:** PiServer camera exposes raw frame age, while the control loop shown does not check it before invoking a non-manual algorithm. CustomDrive updates `last_frame_timestamp` when it retrieves a cached frame, which is not necessarily a new capture. PiSD camera exposes frame sequence/time for a robust guard.

**Design:** place capture timestamps and frame-sequence IDs on perception results, require fresh sequence or acceptable frame age before further autonomous motor commands, and fail safe on repeated/stale frames. Use monotonic time for expiration. Expose last fresh frame age in status.

**Tests:** duplicate frame forever triggers stop; missing frame triggers stop; new frame resumes only under controlled rearm; still-image preview does not imply fresh inference.

### U22 — P2: Make mission recovery and arm stage outcomes explicit (CustomDrive)

**Files:** `CustomDrive/custom_drive/mission_controller.py`; `CustomDrive/custom_drive/mission1_session_app.py`; `CustomDrive/custom_drive/arm_service.py`.

**Evidence:** missions already have a finite-state machine, retries, stop-before-grip, stop-before-release and periodic live updates during pose transitions. The next improvement is more testable stage outcomes and recovery, not rebuilding those accepted flows.

**Design:** introduce structured stage reasons (`target_lost`, `frame_stale`, `arm_unavailable`, `grip_unconfirmed`, `retry_exhausted`), bounded retry/back-out modes, and optional grip confirmation if hardware supports it. Do not claim a confirmed grip without a real sensor. Save a compact mission report after completion/failure.

**Tests:** state/failure transitions with fake camera/motor/arm; stop-before-grip/release maintained; trigger semantics remain `100%=top, 0%=bottom`; recovery does not silently restart movement.

### U23 — P2: Add end-to-end latency and CPU load diagnostics (PiSD/PiServer/CustomDrive)

**Files:** PiSD camera/AI services and status endpoints; PiServer camera/control/model services; CustomDrive Mission 1 runtime.

**Evidence:** PiSD already tracks capture/encoding diagnostics and CustomDrive tracks pipeline FPS. End-to-end capture-to-actuation age, model decode/inference duration and stale-frame events are not uniformly exposed across all runtimes.

**Design:** report rolling p50/p95 for capture, queue wait, resize, inference, postprocess, motor apply and controller loop, plus dropped/stale frame count. Prefer bounded in-memory buffers, disabled or sampled verbose logs, and a hardware-light diagnostic mode. Establish target performance budgets only after measuring Pi 4 hardware, not from guesses.

**Tests:** fake-clock stage timing and bounded metrics buffers; diagnostics impose minimal overhead.

### U24 — P2: Show separate pickup/drop-off trigger lines (CustomDrive Mission 1 UI)

**Files:** `CustomDrive/custom_drive/mission1_session_app.py`; `CustomDrive/custom_drive/mission1_web/static/app.js`; Mission 1 style/templates as necessary.

**Evidence:** latest `CustomDrive_0_5_16` patch notes explicitly state that values are visible in status but separate horizontal trigger guides have not been drawn on the camera overlay.

**Design:** draw distinguishable, labelled grip and drop-off guides over the existing frame, using exactly the accepted conversion (`0%=bottom;100%=top`). Support toggling visibility without changing trigger semantics or the current arm staging.

**Tests:** boundaries and intermediate percentages render at correct Y; guide position matches backend; narrow-screen preview scales correctly.

### U25 — P2: Rebuild YOLO training caches without deleting active readers (CustomTrainer)

**File:** `CustomTrainer/custom_trainer/services/dataset_service.py`.

**Evidence:** `_build_dataset_spec()` performs `shutil.rmtree(cache_root, ignore_errors=True)` before rebuilding `.customtrainer_yolo_cache`. If the cache is in use, a rebuild could invalidate files mid-training. No concurrent failure was reproduced.

**Design:** build an isolated versioned temporary cache with a manifest and validated train/val lists, then promote it after success. Keep old cache while in use and prune only known inactive cache generations with operator-visible policy.

**Tests:** failure mid-build leaves old cache intact; concurrent reader can complete; cache matches source label count.

### U26 — P2: Add disk-space and storage integrity guardrails (PiSD/PiServer)

**Files:** PiSD/PiServer recording services, status reporting and test files.

**Evidence:** inspected recorder paths do not check `shutil.disk_usage`/`statvfs` for a low-space threshold before writing frames. Camera recording can fill limited Raspberry Pi SD-card storage.

**Design:** warn when free space falls below a configurable threshold, stop *recording* safely when writes fail/space is critically low, expose session size and recent write errors, and supply an explicit user-confirmed cleanup flow. Never delete historical sessions automatically by default; never reset saved config.

**Tests:** simulated full disk returns clear error and intact metadata; drive safety behavior unaffected by recording failure.

### U27 — P2: Persist model metadata and verify deployments (piTrainer/CustomTrainer/PiSD/PiServer)

**Files:** existing model export services, runtime model loaders, deploy pages.

**Design:** attach a small backward-compatible sidecar manifest with model kind (steering or YOLO object detection), input geometry, channel/color order, normalization, output interpretation, class names if relevant, quantization mode, training seed and model checksum. Preflight the model using a known synthetic input; retain prior active model on deployment failure. Keep old sidecar-free TFLite models supported through shape inspection and warnings.

**Tests:** wrong model family rejected safely, old models still load, successful new model swaps atomically, invalid model leaves former model active.

### U28 — P2: Define common API statuses and rearm semantics without merging applications

**Files:** PiServer routes/control service; PiSD Flask app; CustomDrive runtime adapters; developer documentation.

**Design:** use a small shared *contract* (not a shared-folder rewrite) for standard status fields: mode, controller owner, camera freshness, model readiness, e-stop, command lease age, last motor error, recording state and current config revision. Specify what allows transition from stopped to armed. Stabilize JSON failure/error codes per component and add contract tests. Keep existing URLs functioning through compatibility adapters.

**Tests:** versioned contract fixture, backwards-compatible old UI behavior, safe cross-client handover.

### U29 — P3: Add safe diagnostics and replay-driven regression tools

**Files:** New component-local `scripts/`/`tests/` only; existing launch paths unchanged.

**Design:** provide a simulation-based 'replay a session' command with synthetic frames and labels, mock motor output and deterministic time. Show predicted steering/confidence beside source labels, session-level MAE and failure events, while never energizing motors. Preserve source session data. Use replay datasets to regression-test model updates and mission behavior before hardware rollout.

**Tests:** deterministic replay over the same fixture, no physical motor initialization, report includes input model/fixture hashes.

## Patch sequence: dependency-aware recommended delivery

| Sequence | Component patch | Scope | Dependencies / gates |
|---|---|---|---|
| 0 | Review baseline/CI checkpoint | Freeze checksums, latest patch notes and reference fixtures | Preserve PiSD V11 and piTrainer V11 over older monorepo copies |
| 1 | PiServer safety | Original F1–F3 and U13 atomic controls (separate security slice if needed) | Zero-motion invalid request, watchdog and e-stop tests |
| 2 | piTrainer data correctness | U11 grouped split, U15 unique saves | Dataset overlap test; both rapid saves preserved; no V11 regression |
| 3 | PiSD AI/recording | Original F4/F5, U20 recovery and U21 fresh-frame guard in separate small patches | Standard validation passing, failure simulation, trainer import fixture |
| 4 | PiBooter reliability/security | U16 corrupt config recovery, then U19 provisioning controls | No lost Wi-Fi config; authentic setup remains usable; auto-exit unchanged |
| 5 | Runtime/model compatibility | U12 runtime dimensions, U27 compatible metadata | Old model still works, new model preflight, safe rollback |
| 6 | CustomDrive ownership/recovery | U14 owner guard, U21 stale frame, U22 stage statuses | Hardware-safe simulation; preserve 0_5_16 trigger behavior |
| 7 | Trainer and YOLO hardening | U17 transactional edits, U18 split/labels, U25 cache | Correct splits, edits and no cache interruptions |
| 8 | Operational visibility/UI | U23 timings, U24 trigger lines, U26 storage guards | Benchmarks, visual checks, no runtime rollback |
| 9 | Cross-component contracts/replay | U28/U29 | Component-local regression and safe simulation |

Do **not** mix the independent component code into one patch zip. Each patch uses only the changed/new component files plus patch notes with exact paths. Verify latest current code and previous three patch notes before release, and do not claim hardware or Windows GUI verification until performed.

## Suggested success metrics

- **Safety:** 0 non-finite motor outputs; expired commands and stale AI frames stop outputs; unauthorized API request moves no hardware.
- **Training quality:** 0 source-frame overlaps between train/val; source counts and split mode are auditable.
- **Data durability:** 0 overwrites across repeated preprocessed saves; interrupted label writes preserve original files; interrupted PiSD recording sessions remain recoverable.
- **Compatibility:** loaders recognize actual TFLite shape and model purpose; old baseline formats continue to work.
- **Availability:** camera, model, arm and connectivity errors appear as explicit statuses rather than silent fallback.
- **Release quality:** all changed components have deterministic tests and forward-only patch packages without user config resets.

## Additional verification performed for this addendum

1. **piTrainer split leakage:** executed `split_by_rows` on synthetic source/flip pairs; confirmed a shared source frame between training and validation with random seed 42. This is a minimal demonstration of the code path, not a measurement from real user training data.
2. **piTrainer repeated save:** ran `save_preprocessed_dataset` twice in a temporary directory within the same second; confirmed both calls returned the same directory and the second overwrote the first recipe and CSV.
3. **PiBooter config:** instantiated `ConfigStore` on a malformed temporary JSON file; confirmed it overwrote the original and did not save a `.bak` file.
4. Static inspection of referenced modules, entry points and recent component patch notes for rollback-sensitive changes.

**Not verified:** physical hardware, live Wi-Fi provisioning, real Flask network traffic, PySide6 GUI interaction, trained TensorFlow/YOLO model inference or actual user data. Many proposal entries describe preventative design improvements, not reproduced production failures.
