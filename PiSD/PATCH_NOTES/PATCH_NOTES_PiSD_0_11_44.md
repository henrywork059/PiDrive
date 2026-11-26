# PiSD 0.11.44 — Consolidated R35 setup accessibility

## Verified baseline
Exact parent 20be5ad4446d8350726abd8645f09a0a0a3b5fed, Linux 45785643038 4/4 and Windows 45785642998 1/1, 36/36 Chromium, PiSD Node 27/27 and standard 63/63, PiServer Node 33/33, Windows Qt 15/15, manifests 7/7 and packages 11/11, forward dry runs 5/5/8. Actual artifacts 15100736466 and 15099279255 inspected in preceding review. Reviewed real launcher, current handlers, canonical R35 and notes 0.11.43/42/41/40; next version absent on main, integration and matching branches.

## Changes
- pisd/web/templates/settings_tab.html and panel_presentation.html: explicit units for 20 Settings and 19 Presentation ranges; attach existing feedback to five settings actions and three presentation actions.
- Corresponding static/js files synchronize aria-valuetext on existing load, input and readout/fill paths. Preserve displayed numeric text, native bounds, autosave, save/apply, configuration and STOP behavior.
- scripts/test_accessibility_r35.cjs: extend existing extracted readout tests and add all-range units/feedback contract. pisd/__init__.py: version marker.
- Shared tools/check_r35_setup.py adds 12 hardware-free setup cases across PiServer and PiSD; existing 36-case browser fixture unchanged. Linux and Windows CI add syntax gates and new regression coverage.

## Verification and limits
Complete changed Python files compiled locally with candidate Git blob hash matching; complete changed JS/CJS syntax checked in V8; three added/updated contracts executed using extracted real functions and mocked DOM. Combined candidate browser/native Qt/package gate pending. No local Chromium or native Qt execution. No config, drive/motor, STOP, authorization or command lease changes. R35 partial; broader contrast/custom themes, screen readers, native touch/hardware/owner acceptance remain. No merge, stable promotion, deployment or Batch 6 advancement.
