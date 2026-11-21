# PiDrive Refinement Roadmap — UI, Workflow, Performance and Maintainability

**Planning date:** 2026-11-22  
**Type:** Addendum to `PiDrive_Code_Review_and_Update_Roadmap.md` (F1–F10) and `PiDrive_Expanded_Update_Roadmap.md` (U11–U29).  
**Sources inspected:** `PiDrive-main.zip`; newer `PiSD_0_11_0.zip` and `piTrainer_0_11_0.zip`; each component's latest patch note and three preceding patch notes when available.  
**Status:** Proposals only. No application code was modified. Web UI and Qt GUI were not interactively rendered, and Raspberry Pi hardware was not exercised. UI findings below describe implementation opportunities, not confirmed visual defects.

## Intent and constraints

A *refinement* makes the existing product more legible, responsive, testable, or maintainable **without removing accepted behavior**. It is different from the safety/correctness fixes already prioritized in F1–F10 and U11–U29.

- Keep current component boundaries and entry points; no forced shared framework, no blanket UI redesign.
- Preserve PiSD V11's unified Start Live, road overlay, manual and AI correction controls, global Space STOP, recording format, and single safety confirmation.
- Preserve piTrainer V11's centralized formatting, dock/splitter flexibility, data sorting, row selection, synthetic frame rules, model save naming, and validation navigation. `RecordPreviewModel` already uses `QAbstractTableModel`; do **not** replace it with an item-per-cell model.
- Preserve PiServer 0_4_x motor/camera/snapshot fixes and its responsive drag pad; keep CustomDrive's Mission 1 grip/drop-off semantics (100% = top and 0% = bottom), arm settings, toggles, and recent GUI changes.
- Do not merge PiServer and CustomDrive's duplicated theme code merely because identical copies exist: prefer tests or explicit sync/version rules until cross-component maintenance is justified.
- Treat configuration files as user data. No settings reset or unrequested version promotion; use separate patch-only packages and notes for each component.

## Recommended refinements

| ID | Priority | Size | Component(s) | User-facing result |
|---|---|---|---|---|
| R30 | P1 | S | PiServer / CustomDrive GUI | Preview displays *Live / Delayed / Disconnected* rather than silently keeping the last image |
| R31 | P1 | M | PiSD / PiServer / CustomDrive | Settings display *Unsaved / Applying / Applied / Failed*, with retry and real backend confirmation |
| R32 | P1 | S | PiSD | Compact and unambiguous AI/manual readiness and control-owner indication |
| R33 | P1 | M | CustomDrive Mission 1 | Readable mission phase timeline, active step, stage elapsed time and last error |
| R34 | P1 | S | PiBooter | Guided connection/recovery state, clear next action, and Wi-Fi failure explanation |
| R35 | P1 | M | All web UI + desktop apps | Consistent keyboard focus, accessible form names, contrast, reduced-motion and touch targets |
| R36 | P2 | M | PiSD / PiServer / CustomDrive | Responsive layouts verified at phone, tablet, compact desktop and full desktop widths |
| R37 | P1 | M | piTrainer | Review selection toolbar showing visible/selected/hidden/synthetic counts and action scope |
| R38 | P2 | M | piTrainer | Profile and bound preview image cache, reduce repeated resize/decode work on large datasets |
| R39 | P2 | M | piTrainer | Consistent nonblocking progress, cancel affordances and final result paths for long tasks |
| R40 | P2 | M | piTrainer | Training-run comparison summary: dataset, split, seed, model, loss and validation metrics |
| R41 | P1 | M | CustomTrainer | Faster annotation workflow with well-scoped shortcuts, zoom/pan and reversible box edits |
| R42 | P2 | S | CustomTrainer | Clear result summary for Validate, Export and Export Validate, linked to exact artifacts |
| R43 | P2 | M | PiServer / CustomDrive / PiSD | Adaptive preview/status polling to reduce idle bandwidth and server work |
| R44 | P1 | S | CustomDrive Mission 1 | Clear pixel/percentage explanation for pickup and drop-off trigger thresholds |
| R45 | P2 | S | PiServer / CustomDrive / piTrainer / PiSD | UI token audit and documented semantic colors/spacing without changing current look |
| R46 | P2 | S | All interfaces | Consistent vocabulary for Preview, Live, Record, Save, Apply, Deploy, Stop, E-Stop |
| R47 | P1 | M | PiServer / PiSD / CustomDrive | Actionable error messages with operation, component, timestamp and request ID |
| R48 | P2 | M | PiBooter / PiServer / PiSD / CustomDrive | Read-only preflight checks for model, camera, motors, storage and connectivity |
| R49 | P2 | S | PiServer / PiSD / CustomDrive | Bounded recent-command/event history usable for support without storing credentials |
| R50 | P1 | M | All | Screenshot/layout and interaction smoke tests anchored to current accepted UI |
| R51 | P2 | M | piTrainer / CustomTrainer | Reproducible experiment card and export-to-deployment traceability UI |
| R52 | P2 | L | CustomDrive / CustomTrainer / PiServer | Extract testable modules from oversized session/UI controllers without altering route APIs |
| R53 | P1 | S | Monorepo | Automated patch manifest, baseline checks and anti-rollback validation before release |

`S` = small isolated patch, `M` = multi-file focused patch, `L` = staged refactor. Sizes are relative complexity, not delivery-time promises.

## Implementation details and acceptance criteria

### R30 — Preview freshness and disconnect visibility
- **Source:** `PiServer/piserver/web/static/app.js::requestPreviewFrame`; `CustomDrive/custom_drive/gui_web/static/app.js` preview handlers.
- **Observation:** PiServer deliberately keeps the last frame when a fetch fails. This is useful for context but may look live after a disconnect; it currently swallows the preview exception in that path.
- **Design:** Display an unobtrusive frame age and Live/Delayed/Disconnected label; retain the last image with an explicit stale overlay. Exponential backoff during disconnect and immediate refresh on reconnection; use monotonic timestamps for age, not filenames.
- **Acceptance:** A failed connection never presents a stale frame as current; recovery resumes preview with no manual page reload; motor safety remains governed by server watchdog, not preview status.

### R31 — Settings transaction feedback
- **Source:** `PiSD/pisd/web/static/js/manual_drive.js` writes local storage and posts `/api/settings`; `PiSD/pisd/web/static/js/ai_mode.js` debounces autosave; `CustomDrive/custom_drive/gui_web/static/app.js` saves configuration; PiServer has separate settings JS.
- **Design:** Show Pending / Applying / Applied / Failed / Conflict with a small save indicator; only mark *Applied* after backend validates and returns effective values. On failure keep edited values visible, permit retry, and show the last server-confirmed values. Do not overwrite a newer edit with an older response (request generation counter).
- **Acceptance:** Simulated offline and invalid-setting cases produce clear, reversible feedback; restarting retains only server-confirmed settings; existing settings schema is unchanged unless migration is necessary.

### R32 — PiSD operating-mode readiness
- **Source:** `PiSD/pisd/web/templates/ai_mode.html`; `PiSD/pisd/web/static/js/ai_mode.js`; `PiSD/pisd/web/templates/manual_drive.html`.
- **Design:** Small readiness strip listing camera, selected model, current control source (AI / correction / manual), motor authorization and current stop reason. Keep the accepted single safety checkbox and minimize explanatory paragraphs.
- **Acceptance:** An operator can tell why motor output is unavailable, or which source is in control, without inspecting logs; Space STOP still always works.

### R33 — Mission 1 progress timeline
- **Source:** `CustomDrive/custom_drive/mission1_session_app.py`; `custom_drive/mission1_web/static/app.js` and `templates/index.html`.
- **Design:** Present phases as `Route → Search → Align → Grip → Transport → Drop-off → Release`, but derive actual displayed stages from the server state machine (do not assume every mission takes every stage). Display current step, last completed step and last failure as read-only state.
- **Acceptance:** During arm settling and camera transitions, page shows progress instead of appearing frozen; no new automatic mission transitions are added by this UI patch. Coordinate with U22 (mission failure semantics).

### R34 — PiBooter onboarding clarity
- **Source:** `PiBooter/pibooter/app.py` creates the onboarding HTML and polls `/api/status`; latest `0_1_1` patch enforces a short startup-window policy.
- **Design:** Explicit network scan / connecting / connected / failed / setup-window-closing states, with context-sensitive guidance. Keep the short auto-exit workflow; never extend hotspot uptime silently.
- **Acceptance:** A failed Wi-Fi connection shows a safe next action without exposing the password or locking the operator into an unexplained transition.

### R35 — Accessibility and input parity
- **Source:** PiSD manual pads already have `tabindex` and labels; PiServer CSS already contains `:focus-visible`; CustomDrive has responsive CSS.
- **Design:** Audit every active control for keyboard focus and accessible name, not replace existing working behavior. Add `aria-live` only where state changes merit announcement; provide reduced-motion styles; ensure touch-only and keyboard-only workflows can reach primary actions. Never add a keyboard shortcut that interferes with text input or bypasses authorization.
- **Acceptance:** Keyboard-only completion of safe setup and non-motor tasks; UI focus is visible; no action relies on color alone. Hardware controls receive separate safety review.

### R36 — Responsive layout verification, not redesign
- **Source:** `PiSD/pisd/web/static/css/pisd_design_system.css` already has multiple breakpoints; PiServer `styles.css` has mobile rules and focus styles; CustomDrive Mission 1 CSS has breakpoints.
- **Design:** Create baseline screenshots and a compact matrix for 390, 768, 1024, 1440 pixel widths. Check camera aspect ratio, drag-pad geometry, panel scrolling, modal viewport fit, and thumb reach. Apply the smallest CSS fixes; preserve PiServer's resizable square drag pad and current docking/panel preferences.
- **Acceptance:** No clipped emergency stop/control labels or inaccessible Save buttons at supported widths; screenshot differences reviewed before merging.

### R37 — piTrainer selection scope clarity
- **Source:** `piTrainer/piTrainer/panels/data/preview_model.py` uses stable source-row mappings and sort-aware `QAbstractTableModel`; current Data controls support multi-selection and soft-delete.
- **Design:** Lightweight toolbar with visible rows, selected rows, hidden rows, generated rows; distinguish “selected visible frames” from “all active frames.” Before bulk edits show exact affected count and whether synthetic derivatives are included.
- **Acceptance:** Filtering, sorting, multi-select and Validation → Edit in Data → Return continue to act on correct stable frame identities. No reintroduction of item-based tables.

### R38 — piTrainer preview memory and throughput
- **Source:** `piTrainer/piTrainer/panels/data/image_preview_panel.py`; `piTrainer/piTrainer/services/data/record_loader_service.py`; prior patch history already optimizes session scans and pixmap reuse.
- **Design:** Measure load latency and peak RSS on small/medium/large datasets; use a memory-bounded LRU for scaled previews only if measurements justify it. Cancel stale image-render work on rapid row navigation; retain current overlays and original image handling.
- **Acceptance:** No stale image/label pairing; memory remains bounded with repeated navigation; no regression in overlay scaling or flip orientation.

### R39 — Unified background-task progress
- **Source:** `piTrainer/piTrainer/services/train/worker.py`, `pages/train_page.py`, preprocessing and export pages.
- **Design:** For each long operation show current step, progress where knowable, cancel/stop where safely supported, and exact output paths. Cancellation must not mark incomplete artifacts as successful; distinguish success, failure, cancelled.
- **Acceptance:** Main window remains responsive during representative operations; interrupted operations do not overwrite accepted models or sessions.

### R40 — Trainer run-to-run comparison
- **Source:** `piTrainer/piTrainer/services/train/history_service.py`, `pages/train_page.py`, validation summary panels.
- **Design:** Save a small sidecar experiment summary (run ID, source groups, split seed/mode, preprocessing hash, model settings, outcome metrics, file paths) and compare two runs by stable IDs. No need for a database in the first iteration.
- **Acceptance:** A saved model can be related to its training data/parameters; missing historical metadata is displayed as Unknown rather than fabricated. Separate from U27's deployment compatibility metadata.

### R41 — CustomTrainer annotation efficiency
- **Source:** `CustomTrainer/custom_trainer/ui/pages/marking_page.py`, `ui/widgets/annotation_canvas.py`; `0_2_11` intentionally narrows the right pane and `0_2_10` refines quick deploy.
- **Design:** Audit current shortcuts, then fill gaps with well-scoped shortcuts for next/previous frame, box selection, zoom/pan, undo/redo and class assignment; put shortcuts in an unobtrusive Help view. Avoid inventing duplicate shortcuts or widening the right pane.
- **Acceptance:** Annotation changes are undoable; shortcuts never fire while typing; quick deploy and the current preview size remain intact.

### R42 — CustomTrainer artifact/result visibility
- **Source:** `CustomTrainer/custom_trainer/ui/pages/export_validate_page.py`, `export_page.py`, `validate_page.py`.
- **Design:** A concise completion summary with result state, last run time, model/dataset names, exact artifact path and an explicit “open location” action when supported. Differentiate native-model validation from exported-model validation.
- **Acceptance:** User can identify which exact model produced reported metrics without opening logs; paths are verified before opening.

### R43 — Adaptive polling and bandwidth
- **Source:** PiServer has a single-in-flight image fetch loop and document visibility handler; CustomDrive Mission 1 refresh intervals are 600 ms status/250 ms frames; CustomDrive GUI polls status at 1500 ms.
- **Design:** Preserve those good backpressure patterns; extend them with inactive-tab throttling, bounded retry and server-reported freshness. Do not alter actual motor control loop frequency or required safety heartbeat. Collect a before/after request-rate profile.
- **Acceptance:** Lower idle HTTP request rate without making active driving controls unresponsive; status recovers quickly on returning to tab.

### R44 — CustomDrive trigger threshold legibility
- **Source:** `CustomDrive/custom_drive/mission1_session_app.py` default arm settings; patch `0_5_16` explicitly defines 100% = frame top, 0% = frame bottom and separate drop-off trigger.
- **Design:** Show 0/50/100 scale and live numeric trigger values adjacent to existing preview markers; name grip and drop-off distinctly. Do not reverse the coordinate convention.
- **Acceptance:** A setting change visibly updates the correct marker; labels and server state agree; refine the UI presentation, while U24 remains the backend/overlay guide change.

### R45 — UI design tokens and drift control
- **Source:** piTrainer's `DOCS/FORMAT_AND_STYLE_GUIDE.md` directs formatting to `ui/formatting.py`, CSS to `ui/styles.py`, colors to `ui/theme.py`. PiServer's and CustomDrive GUI's `theme.js` are byte-identical in the uploaded repo, but remain component-owned files.
- **Design:** Document spacing density, status colors, labels and icon sizing per component, with small smoke tests for accidental token drift. Share policy, not necessarily runtime CSS dependencies. Avoid mass color changes.
- **Acceptance:** New panels follow each component's accepted style without resetting the user's layout or theme preferences.

### R46 — Terminology and empty-state polishing
- **Source:** Existing UI uses terms such as Start Live, AI Preview, Drive, Deploy, Export Validate, Recording, Save/Apply.
- **Design:** Audit each action for *what happens*, *where*, and *whether hardware is involved*. Standardize concise copy and empty states within each app: no camera, no sessions, no models, busy, offline and permission denied. Keep operator-facing text short.
- **Acceptance:** Every empty/error state gives one actionable next step; avoid excess explanatory blocks that crowd live camera panels.

### R47 — Request tracing and errors
- **Source:** PiSD has `pisd/core/errors.py` and error-code docs; PiServer, PiSD and CustomDrive already return JSON API responses.
- **Design:** Attach a correlation ID and operation name to failed API mutations, log the same ID server-side, and provide short UI error text plus expandable details. Redact credentials and sensitive file-path portions from exported diagnostics.
- **Acceptance:** A failed Apply/Start/Deploy can be traced to one bounded log entry; no new sensitive data leaks.

### R48 — Read-only startup/preflight panel
- **Source:** `PiServer` camera diagnostics and `PiSD/scripts/check_ai_runtime.py` already exist; PiBooter provides network status; CustomDrive has PiServer integration and runtime modes.
- **Design:** Reuse underlying health checks in a preflight summary: service mode, camera, model, motor adapter, disk space, network. Explicitly distinguish simulated/mock from real hardware. Do not initialize motors as part of a read-only health check.
- **Acceptance:** An operator sees the reason a feature is disabled; running preflight causes no motor movement or lost settings.

### R49 — Recent-event debug ring buffer
- **Source:** PiServer runtime state and PiBooter state already have bounded log/history mechanisms; CustomDrive uses `debug_tools.py`.
- **Design:** Standardize a fixed-size, on-device event view for operator actions and transitions, with timestamps and outcomes. Show sanitized recent events only; do not create always-on cloud telemetry or log Wi-Fi passwords.
- **Acceptance:** No unbounded memory growth; event log can be copied for troubleshooting; safety STOP events are identifiable.

### R50 — Visual and interactive regression checks
- **Source:** Current CSS/layout guides and many PiSD JS contract tests exist; piTrainer uses PySide6, and components ship independently.
- **Design:** Add small fixture-based browser tests for labels, controls, keyboard focus, responsive geometry and API failure states. For Qt, add offscreen widget construction, stable selection and splitter restore tests where supported. Save baseline images only after explicit review of accepted UI.
- **Acceptance:** New UI patches cannot silently remove the camera panel, resize controls into unusable areas, or regress the selected validation row.

### R51 — Experiment provenance view
- **Source:** PiSD recordings include manifest and labels; piTrainer and CustomTrainer export models with output artifacts. U27 covers deployment metadata.
- **Design:** Display recording-session identity → preprocess run → training run → validation run → exported model → loaded runtime model, marking missing links clearly. Start as locally generated JSON sidecars and a read-only summary; no database or cloud dependency required.
- **Acceptance:** A model's provenance is inspectable when source data exists; historical artifacts remain importable without fabricated fields.

### R52 — Module extraction with behavioral parity
- **Source:** `CustomDrive/custom_drive/mission1_session_app.py` is ~1,914 lines; `CustomTrainer/custom_trainer/ui/pages/marking_page.py` ~1,333; `PiServer/piserver/web/static/app.js` ~1,685. F8 already identified size as a maintenance risk.
- **Design:** Extract pure formatting, validation, stage transition, and DOM/model helpers first. Use adapter-facing interfaces and tests to freeze existing externally visible behavior. Do not rewrite the workflow, rename launchers or move component-owned code into a new shared top-level package.
- **Acceptance:** Identical API routes/config keys, behaviorally equivalent state transitions, no UI/shortcut loss and no patch regressions.

### R53 — Release and anti-rollback checks
- **Source:** The uploaded monorepo includes older PiSD/piTrainer copies than the separately uploaded current baselines; patch notes exist per component. F9 already recommends CI/release improvements.
- **Design:** Generate a patch manifest listing base identifier, new files, modified files, relative paths, hashes and a comparison against recent accepted patches. Refuse a package containing unchanged full component trees, cache/pyc files or unrequested edits. Provide a dry-run apply check against the correct baseline.
- **Acceptance:** A new patch fails validation if it accidentally replaces newer accepted files or changes a different component; notes truthfully list executed tests.

## Priority bundle and dependencies

### Refinement Pack A — immediate operator clarity (small patches)
1. **PiServer R30:** preview Live/Delayed/Disconnected indicator, preserving current preview and camera APIs. Depends on F2 safety watchdog for safety semantics, but UI can be developed independently.
2. **CustomDrive R44:** trigger-scale labels matched to the accepted 0_5_16 semantics; do not duplicate U24's separate overlay implementation.
3. **PiBooter R34:** onboarding status clarity while preserving the short startup window.
4. **piTrainer R37:** selected/visible frame counts and scoped bulk actions; first test stable source-row mapping.

### Refinement Pack B — application state and usability
5. **PiSD R31 + R32:** settings applied feedback, compact AI/manual readiness; verify against 0_11_0 UI and single-confirmation model.
6. **CustomDrive R33:** timeline based only on observed mission state, after U22 makes stage outcomes explicit.
7. **CustomTrainer R41 + R42:** marking shortcut ergonomics and precise validation/export result indicators; keep current quick-deploy layout.
8. **R35 + R36:** accessibility/responsiveness audits and targeted fixes, with accepted UI baselines.

### Refinement Pack C — data/workflow efficiency
9. **piTrainer R38 + R39:** benchmark-driven preview/cache and long-operation progress, after U11/U15/U17 data-integrity fixes.
10. **piTrainer R40 + R51:** training comparison and provenance; coordinate with U27 model metadata.
11. **Runtime R43:** adaptive preview polling, after U21 stale-frame safety and U23 telemetry instrumentation.

### Refinement Pack D — maintainability and release confidence
12. **R45 + R46:** style and terminology audit, selectively and with no cosmetic regression.
13. **R47 + R49:** actionable diagnostic errors and bounded events, leveraging existing logging.
14. **R48:** read-only preflight checks; no accidental hardware actuation.
15. **R50 + R53:** UI smoke tests and patch validation gates, before larger refactors.
16. **R52:** staged module extraction only after regression coverage is in place.

## Concrete review/acceptance matrix

| Surface | Test fixture | Success condition |
|---|---|---|
| PiServer camera | Frame temporarily unavailable, then recovers | Last frame clearly marked stale; fresh state returns automatically |
| PiSD settings | Artificial POST failure and reordering | UI distinguishes pending vs confirmed; no lost newer edit |
| PiSD AI control | Preview only / AI ready / user STOP | Correct control source and stop reason; one safety confirmation retained |
| CustomDrive Mission 1 | Simulated arm settling and drop-off stage | Timeline advances by actual backend state; no fake stage completion |
| PiBooter | Wi-Fi failure during startup window | Clear recovery instruction; existing timeout and security policies intact |
| piTrainer records | 10k synthetic rows, sort/filter/multi-select | Correct stable identity and affected counts; no session selection loss |
| piTrainer images | Rapid next/previous navigation | No stale preview/label pairing; bounded cache memory |
| CustomTrainer marking | Zoom, multi-box edit, undo, typing in fields | No shortcut collisions; current splitter widths preserved |
| Browser layouts | 390 / 768 / 1024 / 1440 px | Primary actions accessible; drag pads remain usable |
| Patch package | Apply to current baseline in temp directory | Only targeted files changed; recent accepted improvements preserved |

## Suggested measurable outcomes

- **Operator clarity:** every critical page exposes its state and stop/recovery reason; no misleading “Live” label on stale video.
- **Save confidence:** 100% of visible “Saved/Applied” confirmations follow successful server acknowledgement.
- **Data accuracy:** row-selection operations resolve by stable record identity after filtering, sorting, and cross-page navigation.
- **Performance:** benchmark median/p95 preview latency, peak memory and requests/second before setting targets; target reductions only when measured.
- **UX safety:** no motor action is hidden under ambiguous UI feedback; keyboard/touch behavior respects existing global STOP and authorization.
- **Release discipline:** 100% of shipped patch files match the intended component/path manifest; no compiled cache files.

## Explicit non-goals

- Do not redesign all interfaces at once, add styling boxes to every panel, or remove useful detailed settings.
- Do not replace piTrainer's PySide6 architecture, data table model, or dock/splitter system.
- Do not merge PiSD, PiServer and CustomDrive into one runtime as part of refinement.
- Do not introduce cloud telemetry, remote control, or new credentials storage as a cosmetic convenience.
- Do not assume a visually polished interface makes safety problems F1–F5 disappear.

## Next implementation choice

Begin with **PiServer R30**, **CustomDrive R44**, **PiBooter R34**, and **piTrainer R37** as four independent, low-rollback refinement patches. In parallel, continue the earlier **P0 safety and dataset-validity work** (F1–F5, U11). Deliver each refinement in its component's established patch format, with latest + prior three relevant patch notes checked, a concrete test list, and truthful verification details.
