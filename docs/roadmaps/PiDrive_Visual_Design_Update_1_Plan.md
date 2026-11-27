# PiDrive — Visual Design Update 1

Date: 2026-11-28 (Taipei/HKT)
Status: **Owner-approved design direction (10/10 decisions); planning only, implementation 0/36.**
Planning baseline: main `3a2a575698a2b89ebd148fbbcaa3d33a8b773c21`.
Scope: PiSD, PiServer, piTrainer and the PiSD Emulator presentation layer, subject to its functional qualification. No implementation, version increment, tag, deployment, stable promotion or new visual baseline is authorized by publication of this plan.

## 1. Purpose and reconciliation

Create a recognizable minimalist professional engineering workspace: a camera-centered driving experience, borderless interfaces, coherent technical typography and two coordinated themes. Build forward on existing software; do not replace working workflows merely to achieve visual consistency.

This is a separate follow-on track from the [original UI/UX roadmap](PiDrive_UI_UX_Improvement_Plan.md), [UI/UX Improvement 2](PiDrive_UI_UX_Improvement_2_Plan.md) and [Performance Optimization](PiDrive_Performance_Optimization_Plan.md). Keep historical 56/56 active proposals and 9/9 completed software batches, the 19 retired proposals and UI2-01–UI2-15 accounting unchanged. Do not count a shared change as complete here without the distinct VD acceptance evidence. Reuse existing primitives, tests and evidence rather than implement competing versions.

Live repository reconciliation at planning time:
- Main was observed at the exact SHA above; the verified recursive tree includes all four in-scope applications and the component-local styling anchors in section 6. Existing roadmap index, UI2, performance, AGENTS.md, emulator roadmap and approved baseline record were read.
- [PR #98](https://github.com/henrywork059/PiDrive/pull/98), open integration of Performance 2.5 and UI2, HEAD `a4b9496b9c5d302b9a574e7e69984d8686b13b4f`; #93, #94, #97 and superseded #92/#95 are not independent replay targets. Preserve all combined runtime, performance, data-column order/semantic parity, security and package gates.
- [PR #99](https://github.com/henrywork059/PiDrive/pull/99), open draft unified 1.0.0 candidate stacked on #98, HEAD `340be98f23c0446151e33da8b790a6ffd16991c8`. This plan neither changes component versions nor treats that candidate as merged, stable or released; respect the owner's separate version authorization and verify actual version/package history before implementation.
- [PR #100](https://github.com/henrywork059/PiDrive/pull/100), open planning-only settings-request flood remediation and emulator qualification, HEAD `c917c707c32aa18a60e728fd77ed5e7821053ce8`. Coordinate SF-01–SF-07; resolve request-flood/feedback-loop risks before touching conflicting settings, layout or theme handlers. Do not add new polling, storage-event loops or duplicate requests for cosmetic reasons.
- The [emulator roadmap](../../PiSD_Emulator/ROADMAP.md) records E01–E03 core/initial implementation with live browser/lifecycle gates still open, E04 connected but unverified with a model, E05/E06 planned. Keep the real PiSD frontend, virtual hardware isolation and separate emulator workspace; no functional emulator milestone is advanced here.
- At execution re-read live main, pending PRs/CI and the actual merged version lineage; do not base runtime work on the older planning SHAs. Existing performance, safety, settings-flood and UI2 regressions take precedence on overlapping files. Independently safe planning may proceed. No integration/merge of other PRs is authorized by this document.
- PiBooter, CustomTrainer, CustomDrive and legacy piCar remain inactive/reference, untouched.

## 2. Owner-approved decisions

| Decision ID | Area | Approved selection |
| --- | --- | --- |
| VD-D01 | Visual identity | A — Minimalist Professional |
| VD-D02 | Color palette | E — Obsidian & Blue |
| VD-D03 | Typography | A — Inter + IBM Plex Mono |
| VD-D04 | Panel geometry | D — Borderless Workspace |
| VD-D05 | Information density | D — Adaptive Density |
| VD-D06 | Icons and controls | D — Contextual Minimal |
| VD-D07 | Navigation | D — Adaptive Professional Workspace |
| VD-D08 | Driving cockpit | C — Immersive HUD |
| VD-D09 | Trainer workspace | D — Task-Adaptive Workspace |
| VD-D10 | Theme system | B — Dark & Light |

Binding additional instruction: **only use Soft Modern when necessary and important**. Ordinary sections use whitespace, subtle dividers and flat surfaces; rounded containers are reserved for important floating controls, dialogs or information needing emphasis. No decorative nested cards, gratuitous pills, gradients, glassmorphism or ornamental shadows. Two curated coordinated themes, not a new custom palette editor/theme library; existing saved customization and supported controls must survive, not be removed or silently reset.

The dark core palette and named font families are approved. Light-theme values, secondary/operational colors, sizing, Lucide asset choice and batch structure are proposed engineering specifications pending validation. Design approval is not visual acceptance of implemented screens.

## 3. Shared design tokens

### 3.1 Theme roles

| Token role | Obsidian dark | Coordinated light (proposed) |
| --- | --- | --- |
| App background | #14171C | #F4F6FA |
| Elevated surface | #20252D | #FFFFFF |
| Subtle divider | #363F4B | #CED5DF |
| Primary accent | #6495FF | #315FD1 |
| Primary text | #EDF1F7 | #20252D |
| Secondary text (proposed) | #A5AFBF | #566171 |

Use dark as the proposed default for new installations, not as a migration reset. Dark/light share hierarchy, spacing, layout behavior and component semantics. Define distinct semantic focus, hover, pressed, disabled, selected, input-boundary and overlay tokens per theme; subtle divider colors are not automatically suitable for meaningful control boundaries. Select appropriate foregrounds (e.g. dark text on dark-theme blue, white on proposed light-theme blue). Validate all meaningful combinations, including overlays on arbitrary camera images; adjust proposed derived values when necessary and document any departure from approved core palette for review. No color-only meaning.

| Operational role | Proposed reference | Meaning |
| --- | --- | --- |
| Success | #22C55E | Ready, confirmed connection/success |
| Warning | #F59E0B | Caution, degraded operation, prerequisite |
| Danger / STOP | #B91C2C | Emergency stop, critical failure |
| Recording | #EF4444 | Explicitly labeled active recording |
| Neutral | #A5AFBF (dark) | Secondary/inactive information |
| Primary | theme accent | Selection, navigation, general action |

Use theme-appropriate contrast variants; preserve existing component-specific semantics (including trainer green execution/amber prerequisites, capture/recording distinctions and all safety controls). Distinguish request pending, confirmed actual state, rejection, stale, disconnected, disabled and failed. STOP must never be confirmation-gated or hidden. Do not recode runtime states purely to fit a palette.

### 3.2 Typography

| Role | Family / weight | Proposed desktop scale |
| --- | --- | --- |
| Page title | Inter 600 | 24 px |
| Section heading | Inter 600 | 16 px |
| General UI | Inter 400 | 14 px |
| Secondary text | Inter 400 | 12–13 px |
| Tables | Inter / IBM Plex Mono | 12–14 px |
| Primary telemetry | IBM Plex Mono | 24–32 px |
| Logs, paths, technical numbers | IBM Plex Mono | 12–13 px |

Use tabular/aligned numerical values and units; mono limited to technical content. Bundle necessary font assets locally after license, size, Qt registration, web loading and offline/fallback checks; include required notices; no CDN. Respect OS scaling and user accessibility preferences; Qt logical sizing must be validated rather than blindly using CSS pixel values.

### 3.3 Geometry and adaptive density

Base spacing 4 px; scale 4/8/12/16/24/32 px. Normal sections borderless; major sections separated by whitespace (typically 16–24 px) or thin subtle dividers. Controls approximately 2–4 px corner radius, important floating controls 4–8 px, important dialogs 8–12 px only when useful. No shadow except justified floating hierarchy. Avoid nested cards. Inputs and focus indicators must retain visible boundaries and sufficient contrast.

Compact desktop data rows approximately 26–30 px; balanced standard desktop controls 32–36 px; larger critical/touch operation targets at least 44 x 44 CSS px and any stricter existing sizes. Do not shrink existing STOP or other critical targets. Density follows task and available space, not an identical fixed grid across components. No clipping at enlarged text or high DPI.

### 3.4 Contextual controls and icons

Prefer a locally hosted, consistent Lucide-style outline icon set, 16–20 px as an initial guideline, readable labels or accessible names, consistent stroke and alignment. Verify licensing/asset cost before adopting Lucide; reuse existing suitable assets. Primary general actions solid accent, secondary outlined where needed, minor toolbar actions borderless, selected state accent plus indicator, disabled state and reason readable, focus visible. Important operations retain text labels and protected state semantics. Toggles, sliders, inputs, tooltips, popovers and keyboard focus return use existing semantics; no hover-only essential controls. Support reduced motion and existing forced-color behavior.

### 3.5 Shared shell, not a fixed layout

Use compact global toolbar, page navigation (collapse where appropriate), contextual toolbar, primary workspace, optional inspector and persistent status information as applicable. Preserve native docking, floating panels, splitters and user layouts. Do not force identical shells across web and native apps. No duplicate navigation or restored trainer Next step control.

## 4. Component-specific specifications

### PiSD — Immersive HUD

Manual Drive and AI Mode use a near-fullscreen, aspect-ratio-preserving camera workspace (not the rejected split/adaptive cockpit default). Minimal readable telemetry overlays and contextual floating controls; compact navigation and persistent status/STOP remain reachable in every mode, including fullscreen and narrow viewports. Retain status-before-preview contract, existing Space STOP and input bindings; presentation cannot bypass arming/safety confirmation, watchdog, stop latch, camera fault or disconnect/visibility behavior. Keep required existing panels and layout features accessible; do not delete controls to make a clean screenshot.

- Distinguish actual manual/AI/control source, model, camera freshness, readiness, faults, recording state and prediction versus applied output. Steering centered bidirectional; throttle direction-aware; use existing units/ranges and linear indicators, not decorative gauges. Do not fabricate live values.
- Use minimum localized opaque or contrast-protected HUD backing as necessary; avoid covering important camera/label/prediction information. Verify bright, dark and complex scenes, image geometry/overlay alignment and safe keyboard/touch reachability.
- Align settings, motor tuning, testing pages, recording/snapshot/session UI and AI readiness with borderless sections, compact contextual tools and accurate apply/readback/persistence. Preserve current AI correction modes, model loading, labels, data format and actual runtime effects.

### PiServer — Modular professional control workspace

Retain dockable/resizable/floating panels, custom presets, settings, device/model/recording management and diagnostics. Improve compact headers, handles, toolbars, camera, telemetry and technical tables; use immersive camera presentation for appropriate driving workspace without removing other panels or saved arrangements. Preserve E-Stop, authorization/CSRF, services, input validation, model-family rejection, effective setting readback, restart persistence, fallback reasons and real control ownership. Status and faults always visible; no purely visual success.

### piTrainer — Task-adaptive workspace

Keep six existing stages, stable navigation, saved layouts, docking, splitters, shortcuts, filtering and playback below preview. Proposed visual focus:

| Stage | Primary workspace |
| --- | --- |
| Data | Compact dataset table, frame preview, playback and label editing |
| Preprocess | Source/processed preview and actual applied configuration |
| Train | Configuration, live curves, progress, logs and comparisons |
| Validate | Stable-row prediction/label comparison, error analysis |
| Export | Model configuration, destination and verified artifacts |
| Export Validation | Compatibility, checks and provenance |

Preserve source-row/column order, visibility/flip and label semantics, bulk-edit safeguards, unique outputs, real cancellation, manifest/checksum linkage, effective run settings, all current performance optimizations and regression contracts. Keep green execution/amber prerequisites. Do not add features solely to mimic a reference app. Chart design: dark/light workspace backgrounds; proposed training blue #6495FF (dark), theme-appropriate light variant; validation amber #FBBF24 with dashed line (contrast-adjusted per theme); muted reference series, thin grid, readable legends/axes, IBM Plex Mono numeric labels, distinguish series with line style as well as color. Preserve values, units, scales, missing data and smoothing disclosure; no 3D/ornamental charts. Retain existing plotting architecture.

### PiSD Emulator — Testing workspace (conditional on functional qualification)

Apply shared themes, typography and controls to its own scenario toolbar, central simulated preview, input/output inspector, virtual GPIO/PWM, logs and existing diagnostics. Keep explicit SIMULATION state independent of theme, actual PiSD page embedding/direct browser link and separate emulator workspace. Never grant physical GPIO authority. Do not duplicate PiSD frontend, imply that simulated data is physical evidence or implement missing fault-injection/replay/log-export features as part of visual styling. Use actual existing capabilities; coordinate E01–E06 and SF remediation; qualify on Windows/Linux before relying on it for evidence.

## 5. Implementation backlog (36 requirements, 11 milestones)

All items are **planned, 0/36 implemented**. Each done condition requires actual evidence, not a screenshot-only assertion. Reuse overlapping UI2 work and tests, but preserve separate accounting.

| Milestone | ID | Requirement and observable acceptance |
| --- | --- | --- |
| VD1 — Visual identity and baseline audit | VD01 | Audit real routes/pages, widgets, handlers, settings and current rendered states. Preserve pinned approved screenshots and record exact commit, CI, fixtures and actual baseline metrics. |
| VD1 | VD02 | Document cross-component semantic design token mapping, approved decisions and intentional exceptions; no shared runtime dependency by default. |
| VD1 | VD03 | Produce representative dark/light prototypes and screen/control inventory against actual code; document proposed changes and baseline comparisons, identify owner-review surfaces. |
| VD2 — Colors and theme system | VD04 | Implement Obsidian & Blue in component-local styles; all applicable surfaces/states use verified semantic tokens. |
| VD2 | VD05 | Implement coordinated light theme with same hierarchy and validated contrast; verify all supported pages and native widgets. |
| VD2 | VD06 | Preserve operational color semantics and non-color state cues across both themes; verify pending/confirmed/rejected/stale/STOP. |
| VD2 | VD07 | Preserve existing settings and layouts, safe theme selection persistence/round-trip/restart and old config compatibility; default only for new installs. |
| VD3 — Typography | VD08 | Integrate local Inter with license, offline rendering, fallback and asset-size evidence in web/Qt. |
| VD3 | VD09 | Integrate local IBM Plex Mono with license, aligned numerical rendering, fallback and offline checks. |
| VD3 | VD10 | Standardize text hierarchy, numeric labels/units and scale without truncation or altered data. |
| VD4 — Icons and controls | VD11 | Establish consistent local outline icon language; verify names/labels, asset provenance, sizing and contrast. |
| VD4 | VD12 | Unify primary, secondary and ghost action appearance while preserving component-specific action priority and behavior. |
| VD4 | VD13 | Refine inputs, sliders and toggles; verify real setting apply/readback and keyboard/touch behavior. |
| VD4 | VD14 | Standardize selected, disabled, hover, pressed and focus states with non-color cues and visible keyboard focus. |
| VD5 — Geometry and density | VD15 | Remove unnecessary decorative containers without removing content/controls or changing runtime state. |
| VD5 | VD16 | Apply borderless section hierarchy; justify selective Soft Modern emphasis, preserve readable input/focus boundaries. |
| VD5 | VD17 | Implement adaptive spacing/density; measure layout and actual critical target sizes, preserve larger requirements. |
| VD6 — Application shells | VD18 | Refine navigation and contextual tools with route/page parity and no extra mandatory core-task steps. |
| VD6 | VD19 | Standardize status bars and optional inspectors; keep actual mode, readiness and faults visible. |
| VD6 | VD20 | Preserve dock/floating, splitters, saved presets and user layout persistence; verify restart and restore. |
| VD7 — Driving interface | VD21 | Implement PiSD near-fullscreen Manual Drive Immersive HUD with aspect ratio, control reachability and real stop/rearm parity. |
| VD7 | VD22 | Apply immersive AI Mode presentation; verify real model/readiness/start/rejection/stop and prediction/applied distinctions. |
| VD7 | VD23 | Refine HUD and telemetry with contrast, correct direction/units, freshness, alignment and bright/dark/complex image evidence. |
| VD7 | VD24 | Align appropriate PiServer camera workspace and qualified emulator presentation; preserve modularity and simulation isolation; test actual existing flows. |
| VD8 — Trainer workspace | VD25 | Refine Data/Preprocess, verify stable rows/columns, filtering, preview, playback and applied recipe behavior. |
| VD8 | VD26 | Refine Train/Validate with real progress, metrics, predictions, failure/cancellation and provenance parity. |
| VD8 | VD27 | Refine Export/Export Validation, verify unique outputs, real artifacts and checksum/manifest compatibility. |
| VD8 | VD28 | Standardize charts, tables, selection and preview styling; compare underlying values and performance on matched fixtures. |
| VD9 — Feedback and interaction states | VD29 | Standardize dialogs/notifications with focus return, recovery and accurate action outcomes; never confirmation-gate STOP. |
| VD9 | VD30 | Standardize loading, empty, failure, disconnected and stale states with actual responses; avoid fake progress or telemetry. |
| VD10 — Responsive and accessibility | VD31 | Verify web desktop/tablet/phone/short-landscape and Qt Windows/Linux high-DPI layouts, keyboard and larger text; no clipping of critical controls. |
| VD10 | VD32 | Verify applicable WCAG 2.2 AA contrast/focus/accessibility, non-color cues, reduced motion and existing stricter interaction targets; record native/physical limits. |
| VD10 | VD33 | Audit cross-component consistency and documented exceptions, preserve supported existing customization and workflows. |
| VD11 — Final qualification | VD34 | Run actual rendered browser/native visual regression matrices; inspect artifacts and compare to pinned historical baseline with explicit intentional differences. |
| VD11 | VD35 | Verify exact revision functional, performance, safety, configuration, package and anti-rollback parity; no weakened test gates. |
| VD11 | VD36 | Produce owner review evidence with exact revision, artifact hashes, before/after, CI, measured limits and separate physical/native acceptance status. |

### Six development batches

| Batch | Milestones | Deliverable / exit gate |
| --- | --- | --- |
| 1 | VD1–VD3 | Baseline/prototypes, themes and typography; exact inventory and approved-history preservation, both themes tested, offline fonts and config parity. |
| 2 | VD4–VD6 | Controls, geometry and application shells; workflow, state, keyboard, target, docking and saved-layout parity. |
| 3 | VD7 | Complete immersive driving presentation; real browser journeys, STOP/rearm and simulated-state qualification; resolve overlapping settings/performance work first. |
| 4 | VD8 | Task-adaptive trainer; native Qt data-to-export workflow, negative cases, stable identity and resource evidence. |
| 5 | VD9–VD10 | Feedback, responsive and accessibility refinement; actual state, viewport, scaling, contrast and focus evidence. |
| 6 | VD11 | Consolidated exact-revision qualification and owner visual review; remaining physical/native/deployment gates explicit. |

Combine related work into substantial milestones; do not create a version for isolated cosmetic changes. At implementation choose versions only under then-current approved version policy and after checking pending/merged versions, package ancestry and latest plus three preceding patch notes per component. No version increment in this planning publication.

## 6. Implementation anchors and safeguards

Verified paths on planning main (recheck before editing):
- PiSD: `PiSD/PiSD.py`, `PiSD/pisd/web/static/css/pisd_design_system.css`, `PiSD/pisd/web/static/css/pisd_layout_system.css`, existing component-specific CSS/templates/JS.
- PiServer: `PiServer/server.py`, `PiServer/piserver/web/static/styles.css` and existing web workspace/theme assets.
- piTrainer: `piTrainer/main.py`, `piTrainer/piTrainer/ui/theme.py`, `piTrainer/piTrainer/ui/styles.py`, existing pages/panels and plotting styles.
- Emulator: `PiSD_Emulator/run_emulator.py`, `PiSD_Emulator/web/assets/app.css` and current UI/service interfaces.

Use existing Python/web and Qt architecture. Document equivalent semantic roles; no cross-component runtime imports merely for visual consistency. No gratuitous React/Tailwind/framework migration, external CDN, external font requests, analytics, new polling, expensive animation or redundant rendering. Evaluate any new asset/dependency for license, security, maintenance, compatibility, offline packaging and cost; material architectural change needs approval. Preserve unknown config keys, existing theme/layout settings, user files, recording/model formats, safety/runtime/auth logic and established paths. Do not use old archives to overwrite current files. Keep actual component patches separate with detailed component PATCH_NOTES and forward-only changed-file packaging per repository rules.

## 7. Acceptance and release gates

Read [AGENTS.md](../../AGENTS.md), [stabilization acceptance](../stabilization_acceptance.md), [visual regression gate](../ui_regression_gate.md), [patch package](../patch_package.md), UI2 and performance plan before implementation. Establish exact baseline and current CI before editing. Resolve failures first; do not reduce existing coverage or weaken performance/safety thresholds.

| Area | Required evidence |
| --- | --- |
| Historical reference | Preserve original 105 web PNGs (83 PiSD, 22 PiServer) from owner-approved source `ba2420536b733659c6cb4796490cdb38f8d31914`. PiSD artifact 15161709968 SHA-256 dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3; PiServer 15162386493 SHA-256 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c; manifest SHA-256 407e870465cbfaecd697c9c5890acc51a5fa23f5953b25027cfd87a1e46f13c5. See [approval record](../ui_baseline_review.md); retain original archives externally before CI expiry. Do not substitute new goldens. |
| Visual evidence | Current pre-change plus candidate screenshots, both themes and representative existing custom settings; inventory paths/viewport/fixture/config/scaling/commit, actual artifact hashes and before/after diffs; distinguish intentional change from regression. Keep existing 78-case web matrix, 105-image baseline comparison, critical target and stricter geometry coverage; expand for new HUD and themes, do not shrink. Native Qt screenshot evidence separate. |
| Responsive and accessibility | Applicable WCAG 2.2 AA: normal text 4.5:1, large text and relevant non-text indicators 3:1; visible focus, names/roles, keyboard order, focus return, non-color cues, reduced motion, supported forced-colors, safe touch. Existing >=44 x 44 critical touch target gate or larger; 390/768/1440 widths and existing short/landscape/large cases, Windows/Linux native high-DPI and larger text. Zero new serious/critical scoped findings; manual assistive-technology acceptance separate. |
| Safety and HUD | Persistent STOP in all layouts and fullscreen; existing stop binding, watchdog, latch, disconnect/visibility and rearm behavior, auth/CSRF, model-family rejection, actual camera freshness and control source preserved. Bright/dark/complex imagery tests, no crop/obscuration, actual preview geometry. Emulator never actuates physical hardware; physical safety tests separate. |
| Workflows and data | Existing suites pass; all required controls perform intended action; actual responses and persisted readback, not mock-only visuals. Test happy/slow/no-data/stale/disconnected/missing-model/rejected-save/invalid-input/recovery/cancel. Preserve exact trainer row/column order and semantics, recording/model/manifest compatibility, output uniqueness and real export. No extra mandatory interactions on core tasks; retain UI2 approved gates. |
| Performance | Matched cold/warm loads, action p50/p95, FPS/age, command latency, request count/bytes, CPU/RSS and trainer interaction/resource workloads where relevant. Preserve stricter performance gates and existing approved shortfalls, do not reset comparison baselines. UI2 proposed p95 non-inferiority within 5% only with adequate repeatability and no weakened stronger gate; document noise/retest. No hidden-tab streaming increase, redundant polling or storage feedback loop. No hardware/energy claims from fixtures. |
| Persistence and migration | Test old/new config, unknown keys, saved theme/layout and settings apply/save/restart; no silent reset; preserve existing customization even though only two new themes are requested. |
| Anti-rollback and release | Check latest actual code, latest and preceding three component patch notes, pending branches/versions, exact CI and forward packaging. No lost accepted features, security/safety fixes or new version collision. No stable promotion, merge, tag, physical deployment or replacement of approved visual references without separate authorization. |
| Owner acceptance | Review actual implementation screenshots and exact source/artifact hashes; distinguish proposed, implemented, scoped automated pass, owner visually accepted and physical/native gates pending. Prior approval of design direction does not certify rendered changes. |

## 8. Research references

References from the design decision process inform patterns, not dependency mandates or copied visual identities. Recheck specific pattern, license/maintenance and compatibility before adoption.

| Reference | Adaptation |
| --- | --- |
| [Linear](https://linear.app/) | Minimalist professional hierarchy and restrained surfaces |
| [Fluent 2](https://fluent2.microsoft.design/) | Contextual transparent actions and coherent workspace hierarchy |
| [IBM Carbon](https://carbondesignsystem.com/) | Semantic colors, technical data presentation and density |
| [QGroundControl](https://docs.qgroundcontrol.com/) | Immersive vehicle operation, readable telemetry |
| [Blender](https://www.blender.org/) | Task-specific professional workspaces |
| [Material Design 3](https://m3.material.io/) | Adaptive layout and theme roles |
| [Lucide](https://lucide.dev/) | Consistent outline icon language; local assets only |
| [Inter](https://rsms.me/inter/) | General interface typography |
| [IBM Plex](https://www.ibm.com/plex/) | Technical/monospaced typography |
| [TensorBoard](https://www.tensorflow.org/tensorboard) | Training curves and numerical monitoring |
| [Qt](https://doc.qt.io/) | Existing native docking/workspace architecture |
| [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/) | Applicable accessibility criteria |
| [Nielsen Norman Group](https://www.nngroup.com/) | Progressive disclosure of secondary diagnostics |

## 9. Status and next authorized boundary

- Design decisions: **10/10 approved**.
- Implementation requirements: **0/36**; milestones **0/11**; batches **0/6**. No application behavior has changed.
- Four applications in visual scope, emulator conditional; two coordinated themes.
- Planning verification: live main and recursive tree, relevant roadmap/approval records and open PR metadata checked. No fresh rendered interface audit, downloaded screenshot verification, application/CI execution, font/icon license qualification, performance measurement or physical testing was performed for this plan.
- Next implementation task, only when separately authorized: Batch 1 baseline audit on latest reconciled main and current CI, establish matched evidence, validate proposed tokens and approved-history retention. No implementation or version changes as part of publishing this plan.
