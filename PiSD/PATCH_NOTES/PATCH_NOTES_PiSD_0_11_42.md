# PiSD 0.11.42 — Batch 4 / R35 Panel Lab non-color state and mock isolation

Exact parent 077232b verified Linux 45754755923 4/4 and Windows 45754755949 1/1. Reviewed real PiSD.py, live Panel Lab template, body rendering/registered handlers, shared focus/forced-colors/reduced-motion CSS, standard validation, canonical R35 and notes 0.11.41/40/39/38.

## Cause and changes
- panel_testing.js: seven visual-only body types had unhandled sample inputs or buttons. Replace fake action buttons with static styled spans, wrap mock bodies inert with visible explanation, retain field examples, real header size/Test/Contract/Last/Expected, global API checks and STOP. No new handlers or endpoint calls.
- panel_testing.css: preserve mock joystick grid using existing classes; add visible underline to actual pressed size button, forced-colors border and reduced-motion suppression of lab hover translation only. Existing shared focus rules and geometry transforms preserved.
- scripts/test_accessibility_r35.cjs and tools/check_browser_ui.py: actual extracted renderer, sample inertness/no native buttons, real controls, normal/forced-colors computed selection/focus checks and existing structure/contract zero-mutation test at four widths.
- version marker and gate notes.

## Verification and limits
Exact parent green, guarded source changes; new exact CI pending. No local browser or hardware test claimed. No config, backend, authorization, API/STOP, motor algorithm, layout persistence or restored Motor Tuning controls. Mock sample inputs are deliberately no longer interactive because they had no actual settings effect. Complete keyboard/touch journeys, broader contrast and active-control audit and owner/physical acceptance remain open. R35 partial.

Verification follow-up before acceptance: require native Tab/Shift+Tab traversal before checking focus-visible in normal and forced-colors modes, rather than assuming programmatic focus following touch/click changes browser input modality. Runtime files unchanged. Exact final candidate CI required.
