# PiServer 0.4.52 — Consolidated R35 setup accessibility

## Verified baseline
Exact parent 20be5ad4446d8350726abd8645f09a0a0a3b5fed, Linux 45785643038 4/4 and Windows 45785642998 1/1, 36/36 Chromium, PiServer Node 33/33, PiSD Node 27/27 and standard 63/63, Windows Qt 15/15, manifests 7/7 and packages 11/11, forward dry runs 5/5/8. Actual artifacts 15100736466 and 15099279255 inspected in preceding review. Reviewed real launcher, current handlers, canonical R35 and notes 0.4.51/50/49/48; next version absent on main, integration and matching branches.

## Changes
- piserver/web/templates/index.html: nine normalized range values and contextual names; existing runtime save banner exposed as status, runtime Save and motor Apply/Retry reference existing feedback.
- piserver/web/static/app.js: announce actual normalized visible readouts instead of integer encoding; curve multiplier pronounced, unchanged banner text not rewritten. Preserve visible values, events, input scaling and backend payloads.
- tests/test_accessibility_r35.cjs: new extracted real readout/markup contract; piserver/app.py version marker only.
- Shared tools/check_r35_setup.py adds 12 hardware-free setup cases across PiServer and PiSD; existing 36-case browser fixture unchanged. Linux and Windows CI add syntax gates and new regression coverage.

## Verification and limits
Full changed Python files compiled locally with candidate Git blob hash matching; complete changed JS/CJS syntax checked in V8; added contract executed using actual extracted functions and mocked DOM. Combined candidate browser, native Qt and packaging gate pending. No local Chromium or native Qt execution. No config, drive/motor, STOP, authorization or command lease changes. R35 partial; broader contrast/custom themes, screen readers, native touch/hardware/owner acceptance remain. No merge, stable promotion, deployment or Batch 6 advancement.
