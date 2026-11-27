# PiSD 0.11.48 — Emulator frame integration repair

Package baseline: b57f02c920cd4d65fe584b8eb4dcf9bd74e6ae71

## Request and root cause
Owner observed the road camera working and direct port 5050 access succeeding, but the embedded page was blocked by the ordinary X-Frame-Options: DENY header.

## Changes
- App factory and access_control: validated emulator-only control port; exact loopback CSP frame-ancestors policy; keep DENY for normal/physical and non-loopback requests. Preserve existing token, mutation origin, safety and settings behavior.
- Emulator runtime/launcher/control app: pass selected control port, reject identical ports, protect controller host and JSON mutations, deny controller framing, publish runtime generation.
- Emulator JS/HTML: reload iframe when runtime generation or URL changes; guard stale status polls; version label.
- Add real Chromium integration and security checks in dedicated CI.
- Update emulator README and component version marker.

## Anti-rollback and verification
Built forward from main 0.11.47; inspected 0.11.47/46/45/44 notes and current launchers, preserved previous performance, layout, recording and STOP code. Draft #94 also provisionally reserves 0.11.48; owner explicitly requested this repair at that version, so #94 requires forward reconciliation before merging. No changes to saved settings or approved screenshots. Exact CI and browser evidence pending; no physical test claimed.

## Shared package qualification
Main's previous merge moved PiServer/trainer package ancestry off the first-parent chain. Port the exact inherited-component guard from pending UI2 branch (already on #93); the previous qualification 46026465707 passed all four jobs, and the component trees are identical to ba05d2ac. Unchanged components may reuse that exact ancestor only if tree hashes match; changed components retain all existing package validation against their own one-step baseline. No package checks removed.
