# PiSD 0.11.41 — R35 Presentation Settings accessibility

Parent a56eb8a exact Linux 45739154326 and Windows 45739154247 passed all five jobs. Reviewed current PiSD launcher, Presentation Settings route/template/handlers, shared focus and STOP rules, original R35, schedule, progress and patch notes 0.11.40/39/38/37.

## Changes
- panel_presentation.html: decorative Run/STOP examples are inert and explicitly identified as visual only. All 19 range controls have visible numeric readouts, excluded from accessible names to preserve native slider semantics. Current preset console is named, focusable and explicitly isolated from global Space STOP. Short status feedback is announced separately from verbose JSON.
- panel_presentation.js: refresh readouts on initial/import/reset fill and native input; report pending save, and distinguish rejected or unavailable backend saves from confirmed success. Existing request payload, local fallback, autosave and layout mechanisms retained.
- test_accessibility_r35.cjs: preserve existing tests; add mock-control/console and actual slider readout regressions.
- tools/check_browser_ui.py: add Presentation Settings at all four widths, native keyboard/touch preview and explicit rejected Save tests with intercepted mutations only.
- Version and shared UI gate notes updated.

## Verification and limitations
Guarded edits against exact parent; new exact CI required. No local browser execution claimed. No motor/authorization/STOP handler, backend/config schema, layout topology, trainer, PiServer or inactive component change. Motor Tuning remains cleared. Broader autosave request ordering and recovery, mobile OS controls, full active-control audit and owner/physical acceptance remain outstanding. R35 remains partial; no merge, deployment or stable promotion.

## Same-version startup correction
Initial CI 45739769345: JavaScript safety/input tests (21/21) and standard validation (63/63) passed, but all four new Chromium Presentation Settings cases failed at initialization, leaving feedback at Loading settings. Source order shows the non-deferred page script captures window.PiSDPanelPresentation before the deferred shared script runs. Defer the dependent page script as well, preserving document order; add a Node script-order guard and explicit browser shared-API availability check. All original interaction assertions remain. No version increment or trainer patch until the corrected combined gate passes. Windows 45739769402 passed. New exact CI required; no local browser execution claimed.

## Revision C — static preview semantics and narrow-screen focus
Revision B a988768: exact Linux 45740059987 failed only PiSD Chromium, Windows 45740059974 passed; combined 4/5. All four Presentation Settings cases now initialized but Playwright still identified the inert native example buttons by role. Node safety/input 22/22 and standard validation 63/63 passed. Replace decorative Run/STOP button elements with styled spans (retain existing classes and inert row); make the static sample console inert because Chromium's native scroll-container focus interrupted Tab order at 390px. Keep real preset console focus and global Space behavior. Preserve all previous browser checks, assert no native buttons in preview grid and inert mock console; update Node static contract.
Local focused Chromium DOM fixture using reconstructed exact Revision B HTML/JS (Git blob hashes checked), same shared presentation and global Space JS, synthetic storage/fetch, inline assets and two older shared CSS files from uploaded archive: four widths 390/768/1024/1440 passed full preview, keyboard traversal and rejected Save assertions after these changes. This was not the complete Flask fixture or exact full repository CSS; no hardware or real persistence tests. New exact combined CI required. R35 remains partial, trainer version unchanged.
