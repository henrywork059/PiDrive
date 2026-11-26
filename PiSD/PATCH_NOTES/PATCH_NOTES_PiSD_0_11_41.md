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
