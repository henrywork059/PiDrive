# PiServer 0.4.44 — Batch 4 / R35 active workspace state and reduced motion

Exact parent 077232b verified Linux 45754755923 4/4 and Windows 45754755949 1/1. Reviewed real server.py, active template, existing aria-pressed updates, styles, current browser/Node suites, canonical R35 and notes 0.4.43/42/41/40.

## Cause and changes
- piserver/web/static/styles.css: active page uses an underline keyed to existing aria-pressed, with forced-colors border. Existing theme, navigation order and focus ring unchanged. Disable decorative snapshot flash in reduced-motion mode; no change to snapshot capture/feedback, joystick transforms or button handlers.
- tests/test_accessibility_r35.cjs and tools/check_browser_ui.py: source contract and actual normal/forced-colors selection/focus computed styles on existing page switch; synthetic flash CSS test without capture request. Existing browser safety and mutation checks retained.
- piserver/app.py version marker only, shared gate notes.

## Verification and limits
Exact parent verified; guarded source changes only, new exact CI pending. No local browser or hardware execution claimed. No API/authorization/STOP, configuration, saved layouts, model/recording, or motor changes. Complete active-control inventory, contrast, touch/keyboard and owner/hardware acceptance remain separate. R35 partial.

Verification follow-up before acceptance: require native Tab/Shift+Tab traversal before checking focus-visible in normal and forced-colors modes, rather than assuming programmatic focus following touch/click changes browser input modality. Runtime files unchanged. Exact final candidate CI required.
