# PiSD 0.11.40 — R35 testing workspace accessibility

Parent 7c70927 verified Linux 45738799996 4/4 and Windows 45738799973 1/1. Reviewed actual PiSD.py, canonical R35, live routes/templates/styles/handlers, existing browser and Node suites, notes 0.11.39/38/37/36.

## Changes
- testing_server.html/js/css: convert endpoint draft shortcuts to native named buttons, using text nodes; preserve draft-only click behavior. Name API request fields and focusable output consoles; native Space in read-only consoles does not trigger global STOP. Preserve explicit STOP and motor arming.
- panel_testing.html/js: name report and panel action/size buttons; announce environment setting; synchronize aria-pressed with actual size on direct, imported, preset and cycle paths. No API or panel topology change.
- test_accessibility_r35.cjs: actual extracted draft-only shortcut and size state regressions, console name/Space semantics.
- tools/check_browser_ui.py: add Testing, Panel Testing and Motor Tuning four-width cases; draft setup and structure/contract inspection, native keyboard/touch activation, focus and zero mutations for inspected tasks. Motor Tuning intentionally has no active calibration controls; retain cleared workspace and test return navigation.
- version and UI gate notes.

## Verification and limits
Exact parent CI green; guarded source edits, new exact CI pending; no local browser or hardware execution claimed. No motor algorithm, authorization, global STOP handler, API, persistent settings, recording-library, trainer or inactive component change. No restoration of removed tuning controls. Mock panel body controls, full keyboard/touch workflows and remaining R35 audit are not certified complete. No merge or stable promotion.
