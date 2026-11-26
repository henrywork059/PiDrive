# Batch 4 — UI regression foundation

Baseline 53b06b7 (CI 45380631288 all four jobs passed). New real Chromium suite intercepts all requests and serves actual current Flask templates and safe GET status from disposable simulation fixtures. All mutations receive synthetic 503; no physical drive, camera start, Save or deletion reaches the runtime. PiServer refuses hardware-capable environments and disables startup camera/control loops. Captures at 390/768/1024/1440 are CI artifacts for owner review, not approved golden images. Browser checks include STOP keyboard focus, primary control geometry, camera panel presence, touch/keyboard presentation opener, PiSD failed settings Save and Retry. Native Qt tests cover named session checkboxes, session-root input, keyboard list resizing, persistence and reset in a disposable INI file. Existing selection identity tests remain. No full journey/Windows/touch-hardware acceptance claimed. R35/R36/R45/R50/UX75 remain pending until evidence and visual review. Use actual screenshots to decide any geometry fixes, not a redesign.

Initial native Chromium gate 45383964152: PiServer dashboard 4/4 and PiSD AI/Settings 8/8 passed; PiSD Manual Drive 0/4 due to a ReferenceError from obsolete writeMotorStartControls in loadSettings. Correct the actual initialization, retain motor-overlay normalization, and require non-default synthetic speed/limit/overlay readback plus modal Save/Apply geometry on the rerun. The first captures are diagnostic baselines, not accepted golden images.

CI 45384279829 passed all four jobs and all 16 Chromium cases; saved Manual Drive speed/limit/overlay restored and modal Save/Apply geometry passed. Further coverage: real modal Tab wrapping and Escape focus return, empty library guards, intercepted STOP requests and native Qt DockPage splitter persistence with zero soft minimums. PiSD dialog focus helper handles Tab only; existing motor and authorization paths unchanged. Captures still require explicit visual review; no physical acceptance.

CI 45396916022 native splitter test failed with 238px difference. Source audit found deferred ratio capture can race queued responsive resize. Correct ordering and use display-independent saved-proportion assertions against original values in piTrainer 0.11.14. Exact corrected CI required; no visual acceptance claim.

CI 45396916022: all PiSD regression/browser checks and manifest checks passed. PiServer browser assertions incorrectly expected zero folders; actual RecorderService creates snapshots at initialization and lists it even with zero images. Correct the fixture expectation to exactly one snapshots folder with zero images and retain empty model assertion, modal focus and intercepted E-STOP checks. No PiServer source/version change. New exact-candidate CI required.

## PiSD 0.11.31 — rejected Settings STOP and retry regression

After the 300f018 fully green four-job gate, the Settings STOP button was found to invoke the settings API without handling a rejected Promise. The synthetic 503 response could leave an unhandled browser error and a success-looking fallback code. The targeted PiSD handler now reports an explicit error code without changing the STOP endpoint, authentication or motor semantics. Browser checks at all four widths exercise a failed Save, retry of the same rejected operation, continued Save enablement, and intercepted STOP rejection with an error code and no page errors. Source-reviewed, exact new candidate CI pending. This checks response reporting only: an intercepted STOP is not proof of physical motor shutdown. Screenshots and Windows/Raspberry Pi acceptance remain outstanding.

## PiServer 0.4.33 — R36 status-metric sizing from real screenshots

Reviewed actual CI 45397236501 Chromium captures. The Status dock showed metric labels and values crossing card borders at narrow, tablet and desktop widths. The existing Status grid was scrollable, but automatic grid-row sizing permitted cards to shrink below their two-line content. The targeted 0.4.33 CSS change sets intrinsic row sizing only inside the Status dock, without changing saved panel dimensions, theme options, or the resizable square driving pad. Real-browser coverage now verifies each Status metric card's rendered content height fits within that card at all four supported viewport widths. Source and screenshot review performed; new exact-candidate CI and updated screenshots pending. Prior captures demonstrate the issue and are not accepted golden images.

## piTrainer 0.11.15 — R50 validation-result edit marker lifecycle

Source audit of ValidationFrameReviewPanel found that marks labelled "Edited in Data after this validation run" survived into a different fresh validation result, even though only the new result should establish the edit timeline. The fix clears edit-group keys only when the result object changes, preserving marks through repeated refresh_from_state() calls for the same result and preserving source/mirror grouping. Native Qt tests cover markers on source and flipped rows, cross-session ID collision isolation, ordinary refresh, new validation, Clear, and exact selected-frame Edit-in-Data identity after sorting. No training, model, records, selected session, layout, or settings code changed. Tests use synthetic in-memory rows with nonexistent image paths. Baseline ffa507d (CI 45416643320 4/4 passed); new exact-candidate CI pending. Native Windows/actual training and owner visual approval remain untested.

## piTrainer 0.11.16 — R50 unloaded generated-frame Edit-in-Data navigation

In the real DataPage route, a generated validation row from an unloaded session was resolved before the session loader had supplied the original. The existing reload path retried source resolution only if it had already succeeded, so Data's synthetic-row exclusion left Edit in Data without a matching row. Now the source resolution reruns after the target session is loaded, preserving the existing session-scoped source-frame identity and multi-session selection. Native offscreen Qt regression exercises actual labels.jsonl fixtures for two sessions with colliding frame IDs, the ValidationFrameReviewPanel button route through the actual MainWindow handler to a real DataPage, generated-source redirect, return selection and an already-loaded no-reload path. Temporary QSettings and tiny fixture frames prevent real user-file modifications. Baseline 1731528, CI 45418879933 all four jobs green; exact updated candidate CI pending. No Windows, hardware or owner golden approval claimed.

CI 45420759869 new real-DataPage R50 test collection failed due to missing matplotlib in the minimal isolated test environment, although it is already a declared trainer app dependency. CI matrix now installs that same declared matplotlib range for the piTrainer regression case; test kept unchanged, exact next CI must verify the actual end-to-end behavior. No release or completion-count increase.

## piTrainer 0.11.17 — R50 label-save/return and pending edit close

Source review found that ImagePreviewPanel debounces steering/speed metadata writes by 450ms, while MainWindow.closeEvent did not flush queued edits. Closing the application before the timer fires can lose those edits; a failed commit also previously discarded the pending records. The targeted fix propagates an explicit success/failure from the DataPage save callback, restores pending edits on rejection/exception, and makes Close synchronously flush or refuse to exit. Source/selection/edit behavior and existing callback compatibility remain. Native Qt tests extend the disposable two-session fixture with source-label modification, unchanged other-session file, updated in-memory data, mirrored validation highlight and return, failure/retry and genuine Qt close refusal/acceptance. Prior 7c7bf08 CI 45421065674 all four jobs passed; exact candidate CI required. No real user data, Windows or physical hardware acceptance claimed.

CI 45424069356: the expanded piTrainer native suite yielded four passing real label-save/return/failure-retry cases and one failed CloseHarness fixture: showing a minimal MainWindow subclass invoked inherited responsive density initialization without _ui_density. The test subclass now neutralizes unrelated density styling only, leaving production MainWindow unchanged. Next exact CI must verify close-event veto/acceptance; no acceptance claim yet.

## piTrainer 0.11.18 — R50 realistic nonzero soft-minimum splitter ratios

The existing splitter restore test used zero soft minimums, but actual Data/Train/Validate presets specify three-panel 260/300/300 or 260/320/300 px. The responsive layout applied saved full-pane ratios only to the leftover space after adding minimums, so a feasible saved 50:25:25 proportion at 1200px became about 430/385/385 rather than 600/300/300. New allocation honors the preferred whole-pane ratios when feasible, freezes only panes below their existing soft minimum, allocates remaining pixels among other panes proportionally and preserves total width with integer rounding. It retains the existing below-soft-minimum fallback, hard QWidget widths, saved QSplitter state and visual density rules. New native offscreen Qt tests exercise actual presets, constrained sizes, narrow visible pane geometry and real DockPage layout save/restore through temporary QSettings. Exact CI and real Windows visual acceptance still required; baseline fd5bc3e CI 45424414919 green.

## PiServer 0.4.34 — UX75/R35 cold disconnected startup and unverified safety telemetry

Live source review after b379138 (CI 45426094777 4/4) found that PiServer init() awaited several read-only endpoints and could abort entirely on a rejected GET, leaving status polling unarmed. When a subsequent /api/status poll failed, the UI showed an error banner but preserved stale E-STOP, drive and output values as if live; clicking the E-STOP toggle could therefore request an unsafe rearm based on the last cached state. A small client-only patch catches each optional initial read independently, always launches automatic status retry, marks the toolbar/status/critical telemetry "offline" / "Unverified" (with live-announced status text), and makes an unverified E-STOP press request STOP only, not rearm. Fresh server status restores the normal UI; REST endpoints, motor algorithms, lease/watchdog, config/storage and layouts are untouched. The hardware-free actual Chromium gate now injects synthetic HTTP 503 into all initial dashboard GET APIs, asserts cold startup, explicit stop request body, and full recovery at 390/768/1024/1440px before running its previous geometry/accessibility checks. All POST mutations remain intercepted. First full candidate CI required; an intercepted STOP is not a physical stop. Native Windows, Pi hardware and owner goldens are still separate.

## PiServer 0.4.35 — UX75 bounded read-only GETs and hanging status polling

The previous 0.4.34 disconnected recovery covered immediate HTTP 503 replies but not an indefinitely pending network request. fetchJson awaited each read-only GET without a deadline; a hung /api/status left statusInFlight true forever, so even backoff/retry code could not run, and a hung initial model/config GET held the rest of startup. Version 0.4.35 adds a 3500ms AbortController deadline only for GETs without an existing caller-provided signal; on timeout callers receive a clear failure and retain their previous retry/error handling. The timer is cleared on success/error, and already externally signaled requests are untouched. Mutating POSTs (especially E-STOP, motor, settings Save) are deliberately excluded from this new client timeout because abort cannot prove whether the operation completed server-side. The actual Flask/Chromium fixture now leaves the initial model GET and a later status GET pending (not 503) and requires timeout, unverified telemetry, STOP-only action, single-flight release, scheduled retry and successful recovery at all four widths. This is browser-side bounded-read protection, not a hardware watchdog. Parent 7fba71c fully green, CI 45431856457; exact new CI required. No Windows, physical Pi or owner golden approval claimed.


## PiServer 0.4.36 — UX75 delayed status after newer acknowledgement

A status GET begun before a newer confirmed snapshot (such as an E-STOP POST acknowledgement) could previously arrive afterwards and overwrite the newer UI state. The status poll now captures the local snapshot revision before fetching and ignores superseded successes and failures, while retaining single-flight cleanup and retry scheduling. This is client-side response ordering, not a motor authority change or a server-clock ordering guarantee. Three deterministic JavaScript cases exercise slow success, superseded success and superseded failure. The actual Chromium fixture holds a status GET, returns a synthetic STOP acknowledgement, then releases the old GET and verifies confirmed STOP telemetry remains until the next fresh poll. All POSTs are intercepted; no backend mutation or physical stop is tested. Parent 05c242f CI 45433987366 passed four jobs; exact new candidate CI pending. No proposal count increase or owner/Windows/hardware acceptance.


## PiServer 0.4.37 — UX75/R35 model library refresh

Exact parent e679901 passed CI 45438129785 (4/4 jobs), including three delayed status tests and four Chromium widths. The model Refresh click previously returned an uncaught rejected promise and reset the operator's selection to the active model. Explicit refresh now catches errors with retry guidance, leaves the previous options intact on failure, preserves a still-listed selection on success, falls back to the existing active/first model selection if removed, and announces refresh feedback through the existing banner. A local list request revision discards superseded replies/errors. Startup and post-mutation default selection behavior remains unchanged. Chromium fixture uses the actual Auto workspace and Refresh control, synthetic model list GET replies, failure/retry, retained and removed selection, empty real list and accessible feedback. All mutations remain intercepted. Exact candidate CI pending; no hardware/Windows/owner acceptance or proposal count increment.


## CI correction — test extraction boundary

CI [45508281272](https://github.com/henrywork059/PiDrive/actions/runs/45508281272) completed with three of four jobs passing; PiServer's native Chromium dashboard passed at 390/768/1024/1440 px, but three existing delayed-status JavaScript cases failed before exercising application logic. The 0.4.36 harness used the exact next-function signature `refreshModels()` as its source extraction boundary; 0.4.37 changes that signature to `refreshModels(preserveSelection = false)`. The correction matches the function name and opening parenthesis instead, retaining the actual pollStatus function, all three cases and every assertion. No application, version, hardware, config or browser-fixture change. New exact-candidate full CI required; 0.4.36 remains the last fully verified candidate until then.


## PiServer 0.4.38 — UX75 recording acknowledgement and folder-read failure

Parent 6b782f7 passed all four jobs in CI 45515079463. A successful recording toggle followed by a failed optional GET /api/record/sessions previously entered the same catch as a rejected POST and reverted the confirmed indicator. Snapshot capture similarly reported an optional read error as a command failure. Scope separates acknowledged commands from folder refresh failures, retains existing rejected-POST rollback and status polling, reports partial success in the status banner and retry guidance in an accessible folder banner. Six deterministic tests execute the actual functions; actual Chromium fixture intercepts recording start/stop, snapshot acknowledgements, failed folder GET and rejected POST at four widths. No mutations forwarded to backend. Exact candidate CI pending; no hardware, Windows, owner acceptance or count increment.


## PiServer 0.4.39 — UX75 saved-folder response ordering

Parent 7ec1be7 passed CI 45517818839 (4/4 jobs). Saved-folder GETs previously captured selection before awaiting the response and applied every reply, including one started before a successful deletion. The browser now uses a local list revision and applies only the current response or error, preserves a still-listed choice made while waiting, and invalidates pending GETs upon an acknowledged deletion. The explicit Refresh banner ignores superseded requests. Nine deterministic actual-function JS cases exercise selection, fallback/empty, startup selection, overlapping success/error, acknowledged deletion and rejected deletion; existing native browser regression remains registered unchanged. No new native browser or physical test result is claimed. Exact candidate CI pending; progress unchanged.


## Test harness correction

CI 45518472203 reported a failed JavaScript step; at inspection its job log was not yet available. Local Node reproduction using the candidate's extracted functions and the new test harness gave 6/9 passing: the three deletion cases accessed the mocked POST before the cross-VM asynchronous confirmation resumed. Await a deferred signal from the actual mocked POST invocation instead of one Promise.resolve() tick. Local extracted-function run after the correction: 9/9 passed, no assertions removed. No application code, version or other test changed. Full exact-commit CI is required.


## piTrainer 0.11.19 — additional R35/UX62 and Batch 5 contract candidate

Parent 8aabfef passed CI 45518657406 (4/4). New native Qt test covers named Validation/TFLite controls, keyboard dataset selection and real-file-only Use Latest helper. Advisory tab icons do not certify model validity. Synthetic disk recording-to-export regression covers current PiSD, PiServer and legacy schemas; no real inference or hardware. Exact new CI pending; owner golden review and Windows acceptance remain separate.


## Additional Batch 4 acceptance coverage

Shared Chromium fixture now exercises the actual PiServer Training folder selector, retained choice on a held GET, synthetic exact-target deletion and stale-list suppression at four widths. Old reads are awaited explicitly and no POST is forwarded. A separate Windows native Qt workflow requires the windows platform plugin and runs selected existing and new interaction suites without skips. The existing four-job Linux gate is unchanged except for registering new tests. Windows hosted runner evidence and owner golden review are distinct. Exact new CI pending.


## Batch 6–9 forward candidates

piTrainer 0.11.20 adds selected-row preview/comparison and contextual help; PiSD 0.11.32 adds bounded local operator events, task-first front page and grouped calibration draft resets; PiServer 0.4.40 adds component-local layout helpers, non-destructive preset previews and optional status tiers. Existing automated gates retained; expanded pure and actual browser tests require exact candidate CI. No owner visual approval or physical acceptance claimed.

PiServer 0.4.40 native browser CI 45538852480 exposed density-control overlap at 390/768/1024/1440. Correction uses a single scrollable Status column with intrinsic children; retain real pointer test and keyboard check. Exact corrected CI pending.


## PiServer 0.4.42 — R35 visual-only style samples
Parent 174026c passed Linux 45555698348 (4/4) and hosted native Windows Qt 45555698560 (1/1). The style preview contained eight dummy form controls in the native keyboard sequence. Mark only these examples inert and exclude inert nodes from the existing dialog focus trap; real settings, preview scrolling, Save/Reset, motor and layout controls remain unchanged. The existing JavaScript suite checks sample isolation and the real Chromium fixture traverses the full dialog Tab sequence at all four widths and checks that actual controls and Save remain reachable. Exact new candidate CI pending; no owner golden or physical acceptance claimed.


## piTrainer 0.11.22 — R35 and Batch 5 workflow evidence
Parent e878c0d passed all five jobs (Linux 45579185459, Windows 45579185711). Explicit training configuration control names, native keyboard field editing and missing/wrong-kind model-file readiness checks added; previous validation results are explicitly historical. Export model status uses the bound training run rather than mutable current split counts, unknown linkage stays Unknown. Native Qt tests run through both existing gates. The real CPU conversion gate now starts from mixed recording fixtures, attaches synthetic run metadata, uses both actual runtime upload/load/inference services, verifies portable provenance, rejected tampering and deletion cleanup, without motor/camera startup or actual training. Test-only OpenCV installed in full trainer smoke environment. Exact candidate CI pending; no proposal closure, owner visual acceptance or hardware claim.


## piTrainer 0.11.23 — UX62/UX64 completion and plot context
Parent 04dbfd9 verified Linux 45580547411 (4/4) and native Windows 45580547521 (1/1), including the real mixed recording-to-both-runtime TFLite contract. F10 meets its original automated acceptance; actual training and hardware remain separate. This follow-up adds local Done indicators for active data, applied preprocessing, in-memory trained model and confirmed existing export files for that exact model, with ready/needed distinct and historical validation results explicitly historical. Training curves identify the active/bound run, row counts and recorded artifact paths; validation plots identify captured model path/source and checksum, use normalized control units and clear obsolete context. Native Qt regression additions use the existing Linux and Windows suites. New exact CI pending; no other proposal closure claimed.


## PiSD 0.11.34 — Batch 4 UX75 bounded Settings reads and retry
Parent e901060 verified Linux 45591973241 (4/4) and Windows 45591973183 (1/1). Settings GETs now have a 3500ms deadline through JSON body completion; POSTs (including STOP) are not given this client timeout. Load uses the shared revision/busy state and visible Loading feedback, handles rejected startup/manual/retry reads without escaping a rejected Promise, preserves edits made during a pending load, and releases the lock on failure. Load/Save/Apply/Reset cannot overlap while reading; STOP remains enabled. Existing accepted backend normalization/readback, apply distinction, reset confirmation and configuration keys retained. Four-width native Chromium fixture now exercises stalled initial GET, rejected retry, successful retry, held read plus draft edit, and previous Save/STOP failure checks; all mutations remain intercepted. Three deterministic feedback state tests added. New exact-candidate CI pending; no physical or owner visual approval.


## piTrainer 0.11.24 — R51 local validation provenance
Parent e9234ab verified Linux 45601026674 (4/4) and Windows 45601026527 (1/1), including PiSD Settings timeout/retry. New Validate and TFLite Check result receipts are written in the captured working folder under validation_runs, unique exclusive-create IDs, actual evaluated-row identity/label hash (not image bytes), model association and metrics; missing linkage stays null/Unknown. Failure to save is reported separately from inference completion. Existing result plots/summary show the receipt path; single-run Compare can inspect the run and its latest five linked local validation summaries without a second run. No model/manifest schema or settings changes, no device deployment claims. Existing native Qt and pure service tests extended; exact CI pending.


## piTrainer 0.11.25 — applied recipe binding and plot artifact access
Parent 462681b verified Linux 45619942932 (4/4) and Windows 45619942897 (1/1). New applied preprocessing binding records the exact ordered active metadata fingerprint and a deep-copied applied recipe; editable/saved draft recipes no longer replace captured provenance. Saved dataset folder linked only for matching active metadata and applied recipe with all expected nonempty files; reset/working folder changes clear the binding. File contents are not rehashed and image bytes are not fingerprinted. Training uses captured recipe/path or Unknown. Both existing plot panels gain explicit Copy artifact paths actions for captured paths, clear them on empty state; training includes captured model-size and saved run summary context. New service/native Qt tests in existing suites. Exact new CI pending; no owner or physical acceptance.


## PiSD 0.11.35 — Batch 4 recording-library read recovery
Parent 95537b4 verified Linux 45621207251 (4/4) and Windows 45621207058 (1/1). Manual Drive and AI recording-folder reads share a 3500ms timeout through body completion, latest-request generation guard and explicit unverified/loading feedback. Preserve selected cached identity on failed reads while blocking Download/Delete until a verified read; recheck exact confirmed target after confirmation; remove acknowledged deletion locally before readback. No mutation timeout or backend/STOP changes. Native four-width Chromium cases exercise populated fixture, actual stalled GET, rejection, retry and empty recovery for both pages; mobile uses tap when visible; hidden AI workspace uses its real button handler. Exact new CI pending; visual and hardware acceptance separate.


## PiSD 0.11.36 — repair 0.11.35 source-contract regression
Parent eae6793 Linux 45630356406 failed PiSD JS R46 copy checks (two) and both standalone AI source-contract checks; all 16 PiSD Chromium viewport cases passed, including eight new folder recovery scenarios. Other three Linux jobs and Windows 45630356385 passed. Restore actionable R46 copy and selected-kind explicit check; move the AI endpoint contract to the real shared reader and assert reader integration/template inclusion instead of deleting it. Add three deterministic actual-reader tests for superseded success/failure, timeout during body, malformed/rejected read and recovery; guard late completion after deadline. Exact new CI pending; no backend/STOP/setting changes or progress increment.


## 2026-11-26 — follow-up test-harness repair (same 0.11.36 runtime)
Exact candidate 092a5dc Linux 45644503886 passed 3/4 jobs; Windows 45644503722 passed 1/1. Both previously failing standalone source-contract validations and all 16 PiSD Chromium viewport cases passed. Only PiSD JavaScript step remained red: new body-deadline test asserted a callback after exactly two Promise microtask yields, but callback was still undefined across the VM boundary. Replace guessed microtask count with explicit body-start promise, assert reader loading and active timer before triggering it, retain all abort/unverified/cleanup assertions and add a 2-second test watchdog. Focused reproduction of the live reader source and revised test passed under local Node.js 22.16.0, once visibly and 10 repeated runs. Full suite not run locally; exact revised candidate CI required. No runtime code, component version, settings, browser test, backend, motor/STOP, inactive component or release change. Keep 0.11.36 unreleased; distinguish candidates by SHA. No proposal closure until verified. Prior browser run emitted pending Playwright route-task cleanup warnings despite passing; not addressed by this narrowly scoped test repair.


## piTrainer 0.11.26 — Batch 5 plot identity and legacy file observation
Parent b5e9095 verified Linux 45730205838 (4/4) and Windows 45730205790 (1/1); PiSD 0.11.36 repair green. Training curves preserve missing epoch positions, use dimensionless loss/metric axis for normalized outputs, expose captured partition fingerprint, recording sessions, recipe fingerprint and existing artifact paths. Validation/TFLite Check plots expose validation ID/evaluated row fingerprint and association with all three plot modes retained. Legacy model files without verified provenance acquire observed file SHA-256 only, no invented run; differing before/after observations clear association. New service/native Qt regressions; exact new CI pending. No image hash, no authentication or proof of immutable file during inference, no owner/hardware acceptance. UX64 scoped closure candidate only after exact CI and review; R51 remains open.


## piTrainer 0.11.27 — R51 portable and legacy inspection
Parent f0e33f6 verified Linux 45732321702 and Windows 45732321842 all five jobs. UX64 scoped implementation gate met: plot units, captured context, artifact copy, missing epochs, all three validation modes and stale-context regression. Compare panel Inspect Model displays selected artifact metadata, verified local sidecar or clearly labelled portable manifest claim, or observed legacy hash without a run. Portable claims never populate/replace local run selectors or create training summaries. Exact file checksum matches local validation receipts separately from run-ID comparisons; invalid present local sidecar or manifest does not fall back. Service/native Qt tests extended, exact new CI pending. No schema, loading, training or layout changes; no physical/owner acceptance.


## piTrainer 0.11.28 — persistent preprocessing receipt (R51)
Parent e24eac1 Linux 45732670276 and Windows 45732670277 all five jobs passed. Successful Apply captures a unique local preprocessing receipt; matching active metadata, selected sessions and working folder required for training linkage; exact receipt checksum required for local Compare/Inspect. Exclusive-create, mismatch, historical and persisted run regression added to existing registered suite. Portable manifest unchanged. Exact new CI pending; no owner, actual training or physical acceptance claimed.


## PiSD 0.11.37 — R35 native disclosure focus and reduced motion
Parent f8d147a piTrainer 0.11.28 verified Linux 45734367606 (4/4) and Windows 45734367599 (1/1). Add summary to shared focus ring selectors including forced colors; prevent front card movement under reduced motion. Extend actual front keyboard Tab/Space and reverse-Tab, focus-ring/computed transform and mobile copy tests at 390/768/1024/1440; retain no-mutation and rejected STOP checks. No motor/STOP or settings changes. Exact new CI pending; R35 remains partial.


## PiServer 0.4.43 — R35 diagnostic input parity
Parent 3024919 Linux 45736191148 (4/4) and Windows 45736191153 (1/1) verified. Native summary Space and read-only event log keys now bypass manual drive keydown; keyup release and body/pad behavior retained. Shared disclosure focus, reduced-motion hover rule, named log and actual extracted-handler/native four-width keyboard and mobile clipboard regressions. All mutations intercepted. Exact new CI pending; no R35 closure or hardware acceptance.


## piTrainer 0.11.29 — R35 desktop setup accessibility
Parent 2e33359 Linux 45736716777 (4/4) and Windows 45736716767 (1/1) verified. Shared disclosure explicit focus/name/description and theme focus style; individually named preprocessing recipe/filter pairs, export destination/artifact options and playback FPS. Native Qt tests cover names, Space/Tab/reverse Tab and editable numeric fields. Existing settings, provenance, data and layout contracts untouched. Exact new CI pending; no R35 closure.


## PiSD 0.11.38 — R35 Manual Drive action-log input parity
Parent c36ad1a verified Linux 45737070868 4/4 and Windows 45737070765 1/1. Disclose expanded state, focus/name read-only log, exclude its native keys from drive/capture/global Space, preserve held-steering release and body/pad STOP. Actual guard and four-width native keyboard/no-mutation/mobile disclosure regression added. Exact CI pending; R35 remains partial; no hardware/owner acceptance.


## PiSD 0.11.39 — R35 AI recording-library input parity
Parent e2b85e1 verified Linux 45738242959 (4/4), Windows 45738242995 (1/1). Named region/selectors, initially locked actions, verified selection announcement, native control keyup isolation with held-steering release preserved. Require visible controls, native keyboard selection/Tab, mobile taps and exact-target cancel/focus; existing failure/retry checks retained. Mobile native select choice uses select_option after tap; no actual download or deletion exercised. Exact CI pending; no R35 closure/hardware acceptance.


## PiSD 0.11.40 — R35 Testing Server and Panel Testing Lab
Parent 7c70927 Linux 45738799996 (4/4), Windows 45738799973 (1/1) verified. Native draft-only endpoint buttons, named custom fields and focusable read-only test outputs; panel lab named actions and pressed state synchronized with actual size across direct/preset/cycle paths. Extend four-width browser matrix with Testing, Panel Testing and intentionally cleared Motor Tuning navigation. No hardware actions invoked by new tests. Exact CI pending; R35 remains partial.


## PiSD 0.11.41 — R35 Presentation Settings

Parent a56eb8a exact Linux 45739154326 and Windows 45739154247 passed 5/5. Presentation mock Run/STOP buttons inert, visible numeric slider readouts, named focusable preset console with local Space semantics and concise live feedback; rejected saves do not announce successful persistence. New four-width real Chromium preview-only and rejected Save journey and two Node checks; exact new CI pending. No actual mutation reaches fixture backend; no hardware or owner acceptance, and R35 remains partial.
