# PiDrive — UI/UX Improvement Plan (UX54–UX75)

**Date:** 2026-11-22  
**Scope:** Planning only; no application files changed.  
**Builds on:** `PiDrive_Code_Review_and_Update_Roadmap.md` (F1–F10), `PiDrive_Expanded_Update_Roadmap.md` (U11–U29), and `PiDrive_Refinement_Roadmap.md` (R30–R53).  
**Source baselines:** `PiSD_0_11_0.zip` and `piTrainer_0_11_0.zip` for those components; `PiDrive-main.zip` for PiServer, PiBooter, CustomDrive, and CustomTrainer.  
**Evidence limitation:** UI templates, styles, controller code, design documentation, and latest/preceding patch notes were inspected. Actual web pages, mobile interactions, Qt GUI visuals, and Pi hardware have *not* been interactively tested. Layout findings are design opportunities, not measured usability defects.

## 1. Objective and non-negotiable constraints

Make everyday actions clear, fast, accessible, and predictable while keeping advanced controls available. Prioritize *camera/preview → current state → primary operation → secondary settings and logs*. Avoid adding more panels or paragraph-length instructions simply for visual polish.

- **PiSD:** Preserve V11's shorter AI Mode text, one motor-safety confirmation, status-before-preview layout, unified camera start, overlay, record/snapshot, global Space STOP, and always-available STOP; use `pisd_layout_system.css` last in the documented CSS loading order.
- **PiServer:** Preserve existing manual/training/auto/camera/motor navigation, custom panel resizing and saved layouts, theme customization, tuning, and E-Stop behavior.
- **piTrainer:** Preserve V11 six-step numbered workflow, compact banners, splitter and scrolling behavior, keyboard shortcuts, row identity, soft-delete, playback below preview, Training/Validation navigation, amber prerequisite and green main-action conventions. **Do not restore the removed “Next step” UI.** Use `ui/formatting.py`, `ui/styles.py`, and `ui/theme.py`.
- **CustomDrive:** Preserve working GUI/headless/web paths, live integrations, saved settings, Mission 1 pose semantics, `100% = top / 0% = bottom` grip/drop-off percentages and existing stop behavior.
- **CustomTrainer:** Preserve 0_2_11 Marking-tab preview-width refinement, lightweight quick deploy, selected-frame deployment and remembered splitter behavior.
- **PiBooter:** Preserve the `0_1_1` short startup window (5 seconds) and hotspot/connection lifecycle. Do not turn its UI into a heavy app that delays boot.
- **All components:** No unrequested directory moves, new design framework, runtime config reset, or cross-component source sharing. Use patch-only delivery with component-specific notes if changes are later requested.

## 2. Screen architecture — what to emphasize

### PiSD — Manual Drive / AI Mode

**Desktop:** `[Mode and connection state]` → `[Status summary]` → `[Large live camera | Manual/AI controls]` → `[Always-visible STOP]` → `[Saved recordings, advanced settings, logs]`.

**Phone:** Status first → camera → primary drive/AI controls → fixed reachable STOP → expandable recordings/settings. Follow established PiSD semantic role ordering rather than inventing a new grid system. Keep numeric overlay calibration in its existing advanced dialog; do not add a second separate motor confirmation.

### PiServer — Multi-panel workspace

**Default Manual layout:** `[Run state, motor output, camera and model]` as a compact status row, `[camera preview]` as the dominant workspace, `[manual controls]` adjacent, `E-Stop` visually persistent, `Tuning / recordings / diagnostic values` available in collapsible or resizable panels. Allow all panels and their current layout persistence to continue working. Changes must remain compatible with saved layouts.

### piTrainer — Six-stage workflow

**Persistent page tabs:** `Data → Preprocess → Train → Validate → Export → Export Validation`. Within each page maintain `[Workflow controls | Review table/plot | Preview]`. Use short prerequisite/result indicators (e.g. selected data count, model loaded) rather than extra Next buttons or explanatory blocks. Preserve page-local splitter sizes and active row.

### CustomTrainer — Marking-first workflow

`[Compact frame/session actions | LARGE image canvas | Narrow selected-box/class editor]`. The latest patch deliberately shrank the right panel; the image must remain central. Place quick deploy adjacent to review controls, with mode/selection scope clearly stated.

### CustomDrive — Mission setup and execution

**Before run:** `[Route + model + essential run options]` with `Advanced motion thresholds` and `Arm poses` collapsed by default, but accessible. **While running:** `[Annotated camera + mission state + stop]` as the dominant view; current arm/motor state and errors nearby. Do not hide a running mission's safety state behind setup fields.

### PiBooter — Phone onboarding

`[Choose Wi-Fi] → [Enter credentials] → [Connecting] → [Connected: IP/next step]`. Keep polling and static CSS lightweight; ensure failure returns to the editable form with the SSID preserved and password handled safely.

## 3. Proposed new improvements (avoid duplication with R30–R53)

| ID | Priority | Size | Component | Specific improvement | Implementation direction and done condition |
|---|---|---|---|---|---|
| UX54 | P1 | S | PiSD | **Task-first start page** | Front page should clearly distinguish `Manual Drive`, `AI Mode`, `Diagnostics/Settings`; last-used operating mode can be shown as context, never auto-arm motors. Preserve current routes. |
| UX55 | P1 | M | PiSD | **Preview-first information hierarchy** | Adjust typography/panel emphasis, not semantic DOM order; keep camera prominent, status first, motor controls reachable, STOP visible at all sizes. No camera/control overlap at 390/768/1440 px. |
| UX56 | P1 | S | PiSD | **Recording mini-toolbar** | Near current camera preview, show recording state, duration/frame counter when available, snapshot outcome, and current session name. Use backend-confirmed facts; no fabricated frames or names. |
| UX57 | P2 | S | PiSD | **Advanced calibration ergonomics** | Reorganize the existing seven numeric visual-tuning inputs into `Geometry` and `Appearance`, with visible units, a single apply action, and a clearly scoped reset. Never auto-reset saved values. |
| UX58 | P1 | M | PiServer | **Tiered status density** | Current Status panel has many metric cards (`Drive`, `Output`, `Target`, `Last save`, `Preview`, `Camera`, etc.). Keep 4–6 essentials visible; put FPS/backend/bias and diagnostics behind `More telemetry` while retaining all data. Keep saved panel/layout behavior. |
| UX59 | P1 | S | PiServer | **Primary versus secondary actions** | Visually separate `Start/Record/Apply` from `Save layout`, `Refresh`, `Reset layout`, `Delete`; user should distinguish device action, layout action, and destructive action immediately. Existing APIs unchanged. |
| UX60 | P2 | M | PiServer | **Operator layout presets** | Offer non-destructive `Driving`, `Camera tuning`, `Model testing` panel configurations in addition to current saved custom layout. Preview and cancel preset change; never overwrite custom saved layout without approval. |
| UX61 | P1 | M | piTrainer | **Contextual bulk-edit preview** | Before action on selected rows, show the exact frame count, fields being changed, and a few representative old→new values. Preserve existing soft/hard-delete confirmations and selected row identity. |
| UX62 | P1 | S | piTrainer | **Prerequisite markers on existing six tabs** | Show understated `ready / needed / done` hints for active data, preprocess output, loaded model and export. *No* extra `Next step` button and no change to tab order. |
| UX63 | P1 | M | piTrainer | **Synchronized review comparison** | Add an optional compare mode for label vs deployed prediction on the same selected frame, with difference values next to the image; sorting/filtering must not change the comparison identity. Build on existing Data Review model deployment. |
| UX64 | P2 | M | piTrainer | **Readable plot and experiment context** | Every training/validation plot gets legible axis units, selected run/model/dataset identity, and direct access to the saved artifact path. Preserve existing plots; do not show precision unsupported by data. |
| UX65 | P2 | S | piTrainer | **Contextual shortcut/help overlay** | A compact keyboard-shortcuts panel specific to current page clarifies row navigation, playback, soft delete and hard-delete warning. Do not intercept Space while typing or overwrite existing mappings. |
| UX66 | P1 | M | CustomTrainer | **Canvas-dominant marking composition** | Keep the accepted narrow right panel and large frame canvas; place highest-frequency box/class actions in a slim, stable tool row without expanding the editor. Support existing splitters. |
| UX67 | P2 | S | CustomTrainer | **Annotation class clarity** | Pair each annotation class color with a readable text label and selection border; provide colorblind-safe non-color cues and show active class when creating a box. Never change saved class IDs. |
| UX68 | P2 | M | CustomTrainer | **Review queue / issue triage** | Create a read-only filter for missing labels, invalid boxes or low-confidence predictions, with direct jump to selected frame and reversible annotation edits. Coordinate with dataset validation update U18. |
| UX69 | P1 | M | CustomDrive Mission 1 | **Progressive disclosure of setup** | Current mission page exposes many speed/IoU/timing/pose fields before the preview. Show essential `Route`, `Model`, `Start/Stop`; move advanced tuning into expandable groups and persist open/closed UI only, not new run defaults. |
| UX70 | P1 | S | CustomDrive Mission 1 | **Pre-run summary** | Before Start, concise summary: route parsed, model selected, live vs simulation, camera/arm availability, grip/drop-off trigger percentages. Blocking errors are distinct from informational notes. Avoid claims unless backed by runtime state. |
| UX71 | P1 | M | CustomDrive | **Arm control readability** | In GUI/web manual arm panel, align each `Servo n + / −` pair with current angle or target and bounded range when available; distinguish jog from saved pose actions. Preserve actual servo semantics. |
| UX72 | P2 | S | PiBooter | **Tap-to-select Wi-Fi polish** | Existing `fillSsid` tap-to-fill remains. Add clear selected network feedback, signal/security explanation where available, show/hide password toggle, and keyboard-friendly submit/return. Do not log or persist passwords in the UI. |
| UX73 | P1 | S | PiBooter | **Connected-state finish screen** | On successful Wi-Fi join, emphasize assigned IP, next access action, and connection result in a phone-friendly short page. Never assume mDNS works. Preserve 5-second discovery-window logic. |
| UX74 | P1 | M | All | **Destructive-action clarity** | `Delete model/record/session` confirmation names the exact target and permanence; prevent double-submit; show undo only when technically supported. E-Stop must be immediate, never confirmation-gated. |
| UX75 | P1 | M | All | **UI acceptance and usability checks** | Establish repeatable visual and interaction tests for happy path, slow path, disconnected state, no-data state, keyboard, touch, focus restore and responsive widths; test against accepted baseline screenshots before applying cosmetic patches. Builds on R35/R36/R50 rather than replacing them. |

Sizing: **S** small focused edit, **M** multi-file focused patch. These are relative scopes, not time estimates.

## 4. Detailed page-level change examples

### PiSD Manual Drive
- Keep `[Status]` above `[Camera]` and `[Drive]`, never push STOP into a hidden drawer.
- Group `Start live`, `Snapshot`, `Record` as a camera/recording action strip; `STOP motors` remains visually and semantically separate.
- When recording is on, show a text label + timer; not only a red circle. Show recent snapshot filename only on confirmed successful response.
- Keep overlay visual calibration numeric and in the existing modal; group the seven controls without changing their definitions or defaults.
- Do not add a second safety checkbox.

**Code touch points:** `PiSD/pisd/web/templates/manual_drive.html`, `pisd/web/static/css/manual_drive.css`, `pisd/web/static/js/manual_drive.js`, `pisd/web/static/css/pisd_layout_system.css` (last-resort layout changes only), `pisd/core/presentation_registry.py`.

### PiSD AI Mode
- Show model name, camera state, actual control source and STOP reason in a compact operator strip (build on R32).
- Prioritize the preview and one main run action; retain available correction modes without moving controls to unrelated sections.
- Avoid reintroducing descriptive paragraphs removed in 0_11_0.

**Code touch points:** `PiSD/pisd/web/templates/ai_mode.html`, `pisd/web/static/css/ai_mode.css`, `pisd/web/static/js/ai_mode.js`.

### PiServer
- Current `piserver/web/templates/index.html` has a dense Status section with numerous metric cards plus independently resizable panels and style settings. Tier the cards rather than deleting them.
- Preserve theme editing and Save/Reset layout behavior. Additional presets must not replace saved user layout without approval.
- Group motor/camera tuning controls under current page tabs; make command effects and confirmations explicit.

**Code touch points:** `PiServer/piserver/web/templates/index.html`, `piserver/web/static/styles.css`, `piserver/web/static/app.js`, `piserver/web/static/theme.js` (only when tokens need adjustment).

### piTrainer
- Implement UX61 in Data Review's existing bulk editor, with preview of fields and selected records before mutation.
- Add tab status without adding forbidden Next step controls; preserve page banner and green main / amber prerequisite semantics.
- Implement compare mode using stable source-record identity after filtering/sorting; ensure predictions and labels refer to exactly the same frame.
- Keep playback directly below frame preview; restore splitter positions after returning from Validation.

**Code touch points:** `piTrainer/piTrainer/pages/data_page.py`, `piTrainer/piTrainer/panels/data/bulk_edit_panel.py`, `piTrainer/piTrainer/panels/data/preview_model.py`, `piTrainer/piTrainer/panels/data/image_preview_panel.py`, `piTrainer/piTrainer/pages/validation_page.py`, `piTrainer/piTrainer/ui/formatting.py`, `styles.py`, `theme.py`.

### CustomTrainer
- Avoid expanding the right pane after 0_2_11. Put box actions close to the preview canvas and keep a compact class editor.
- Make invalid/missing labeling cases filterable rather than requiring users to hunt through all frames.

**Code touch points:** `CustomTrainer/custom_trainer/ui/pages/marking_page.py`, `custom_trainer/ui/widgets/annotation_canvas.py`, `custom_trainer/ui/styles.py`.

### CustomDrive
- Before a mission, emphasize setup essentials; after start, emphasize state and annotated preview. Do not destroy/edit runtime config on panel collapse.
- Keep arm pose tables accessible, with any advanced values hidden only by UI disclosure; preserve saved numerical values and trigger-axis semantics.
- Always show STOP and real/simulated hardware mode (build on existing R33 timeline and U14 hardware owner work).

**Code touch points:** `CustomDrive/custom_drive/mission1_web/templates/index.html`, `custom_drive/mission1_web/static/styles.css`, `custom_drive/mission1_web/static/app.js`, `custom_drive/gui_web/templates/index.html`, `custom_drive/gui_web/static/app.js`.

### PiBooter
- Current onboarding HTML/CSS is generated in `PiBooter/pibooter/app.py`, including `fillSsid` and `/api/status` polling. Keep it lightweight and offline-capable.
- A failed network join should keep the editable SSID, explain the recovery choice, and avoid revealing/relogging the Wi-Fi password.

**Code touch points:** `PiBooter/pibooter/app.py`, relevant current network/status helpers (inspect before modification).

## 5. UI visual system (incremental, not a global rebrand)

- **Hierarchy:** one primary action per task group; secondary tools have quieter treatment; dangerous/destructive controls are explicit and separated from frequent operations.
- **Color semantics:** obey existing project palettes, not one shared theme package. PiSD's `primary` cyan, success green, caution amber, danger red/pink; piTrainer's established green main and amber prerequisite actions. Never communicate state through color alone.
- **Density:** preserve compact headers and dock/splitter sizes. Use targeted grouping and whitespace rather than increasing every component's padding.
- **Form layout:** label + value + units, validate close to the input, reflect backend-effective values only after confirmed Apply.
- **Touch and keyboard:** meet WCAG 2.2 AA relevant success criteria (including 24x24 CSS px target minimum with exceptions; provide larger touch targets where feasible, focus visibility, no-drag alternative for essential drag controls); use 4.5:1 normal-text contrast. See https://www.w3.org/TR/WCAG22/ .
- **State:** distinguish disabled, pending, running, completed, error, disconnected and stale; never make a stale camera image look live (R30).
- **Dialogs:** use one coherent Apply/Cancel path; focus and Escape should work; protect unsaved form edits; STOP must stay operative per existing safety contracts.
- **Empty states:** exactly one next useful action; avoid long explanatory paragraphs in mission and live-control screens.

## 6. Patch packages in recommended order

### UX Pack 1 — Immediate visibility and navigation
1. PiServer **UX58 + UX59**, after controller safety work; keep same APIs and current layout persistence.
2. PiSD **UX55 + UX56**, after PiSD AI validation and command watchdog repair; preserve latest `0_11_0` layout rules.
3. CustomTrainer **UX66 + UX67**, based on current 0_2_11 Marking width fix.
4. PiBooter **UX72 + UX73**, keeping short startup behavior and no credential leaks.

### UX Pack 2 — Workflow efficiency
5. piTrainer **UX61 + UX62** (selection identity and bulk-edit preview); then **UX63** compare mode.
6. CustomDrive **UX69 + UX70** (mission setup disclosure and pre-run summary); then **UX71** arm readability.
7. PiServer **UX60** optional layout presets, with non-destructive apply preview.

### UX Pack 3 — Advanced review and release assurance
8. piTrainer **UX64 + UX65**, consistent data/model metadata and shortcuts.
9. CustomTrainer **UX68** triage, after dataset integrity validation.
10. All **UX74 + UX75**, integrating cross-component UI acceptance gates with R35/R36/R50.

**Dependencies:** F/U safety and data-integrity fixes remain release blockers; UI refinements must not be used to disguise missing backend authorization, motor watchdog, model-shape compatibility or data validation. R30–R53 are still active and complementary.

## 7. Acceptance matrix

| User journey | Mandatory check |
|---|---|
| PiSD Manual: open camera → record → snapshot → stop | Clear actual recording/capture state; STOP reachable; no change to saved recording paths/labels |
| PiSD AI: select model → start → correct → stop | One accepted safety confirmation; short copy; actual motor source displayed; Space STOP still works |
| PiServer: drive → camera tune → restore layout | Status glanceable; E-Stop persists; user's saved layout/theme unchanged unless explicitly saved |
| piTrainer: filter/sort → select many rows → bulk-edit → Validate → back | Exact row identity and counts; reversible actions where designed; same selected frame/sessions retained |
| piTrainer: Train → Validate → Export | No fake progress; result/paths accurate; model files not overwritten |
| CustomTrainer: annotate large image → deploy selected frames | Preview width at least as usable as 0_2_11; class IDs/quick deploy unchanged |
| CustomDrive: configure route → review readiness → execute Mission 1 | Advanced settings preserved; actual stage shown; `100 top / 0 bottom` thresholds remain unchanged; STOP available |
| PiBooter: join hotspot → select Wi-Fi → connect/fail | Existing 5-second discovery behavior; password not exposed in logs; reachable next step shown |
| Web: 390/768/1024/1440 wide, keyboard-only and touch | No clipped primary/STOP controls, no inaccessible focus, no state communicated only via color |
| Patch packaging | Changed-files-only archive, exact relative paths, detailed patch notes and latest + three previous patch-note anti-rollback comparison |

## 8. Measurement plan

Do a small *baseline-before-patch* usability test with recordings or scripted interactions; measure rather than claiming untested gains:

- Click/interaction count: open live preview, start and download recording, save tuning, return from Validation to same row, complete Mission 1 setup.
- Findability: whether a tester identifies live camera vs stale, current motor control source, selected frame scope, actual saved artifact path, and STOP in 5 seconds.
- Task success: wrong target deletions, accidental setting resets, repeated attempts, keyboard/touch failures.
- Screen efficiency: preview usable area at 390 and 1440 widths, clipping/scrolling burden, number of persistent high-salience controls.
- Performance: interaction response latency, focus/selection stability, and total memory for large Qt tables.

**Completion condition:** Before-after evidence supports an improvement; no accepted user behavior or safety guarantee disappears, and no untested visual change is represented as an established defect fix.

## 9. External reference

- World Wide Web Consortium. *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/ . This is used for accessibility acceptance criteria, not as evidence of a PiDrive bug.
