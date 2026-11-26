# PiSD 0.11.37 — R35 native disclosure focus and reduced motion

Parent f8d147a (piTrainer 0.11.28) verified Linux 45734367606 4/4 and Windows 45734367599 1/1. Reviewed current PiSD.py, original R35 acceptance, actual front templates/CSS, existing browser and JavaScript suites and notes 0.11.36/35/34/33.

## Cause and changes
- pisd/web/static/css/pisd_design_system.css: native summary elements were omitted from shared focus styles; include them in normal, pointer and forced-colors selectors without changing tokens.
- pisd/web/static/css/front_page.css: suppress mode-card translation on focus/hover only under reduced-motion preference; normal presentation remains unchanged.
- scripts/test_ui_style_tokens_r45.cjs: assert normal/forced-colors summary coverage and reduced-motion card rule.
- tools/check_browser_ui.py: traverse final mode card → collapsed preflight → recent events → refresh → copy using real Tab/Space and reverse Tab at all four widths; assert shared disclosure focus ring and no reduced-motion card translation; also tap copy on mobile. Existing read-only mutation and rejected STOP assertions retained.
- pisd/__init__.py, shared regression gate notes: version/evidence.

## Verification and limits
Exact parent CI green. Guarded source edits only; new exact CI pending. No motor/STOP handler, authorization, API, configuration, layout, model provenance, recording-library, PiServer, trainer or inactive component changes. No local browser execution or hardware/owner acceptance claimed. R35 remains partial: wider active-control and touch audit still required.
