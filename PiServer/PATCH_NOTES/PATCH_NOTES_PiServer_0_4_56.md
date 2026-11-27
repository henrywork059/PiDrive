# PiServer 0.4.56 — UI2 verified dashboard status (provisional)

Package baseline: b57f02c920cd4d65fe584b8eb4dcf9bd74e6ae71

## Request, cause and scope
UI2-02/03/07/08: initial dashboard asserted run/ready/E-STOP OFF before status verification; offline handling invalidated only three drive metrics and left cached model/camera/error/algorithm and tuning telemetry looking live. Repeated status writes also caused redundant DOM changes. Reviewed actual server.py, dashboard, controller, current 0.4.55 and prior 0.4.54/53/52 notes. Preserve merged performance work and user-controlled dock layout.

## Changes
- piserver/web/templates/index.html: initialize runtime status, server metrics and E-STOP as unverified pending a successful read. The existing STOP control remains available; existing JS decides engagement/rearm.
- piserver/web/static/app.js: on unsuccessful status read invalidate 12 server observations; preserve local target and confirmed last-save history with a clear historical title. Successful reads restore actual values. Avoid unchanged status text and banner class writes. No polling cadence, request payload, preview ownership, safety, auth or runtime configuration changes.
- tests/test_ui_copy_r46.cjs: deterministic startup/offline regression of actual function; tools/check_browser_ui.py extends existing multi-width disconnected/recovered assertions without removing earlier STOP/timeout/late-response tests.
- piserver/app.py version marker; shared forward package harness ports exact identical-component guard from concurrent PR #93, preserving ancestry, path, history and integrity assertions.

## Verification and limits
Actual modified JS syntax checked using V8. Extracted actual markStatusUnverified function verified 12 server values invalidated, local target and last confirmed save retained, initial STOP mixed. Prior Linux component regression passed; new exact browser/Node/Python/package CI and visual comparison pending. Not a hardware or performance certification. No default preview profile, config, custom style/layout, device command or persistence change. No merge/stable promotion.
