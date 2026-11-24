# PiBooter 0_1_5 — R35 keyboard access and reduced motion

## Request
Implement the PiBooter share of R35 accessibility/input parity: keyboard-only operation of safe setup forms and existing non-motor tasks, visible focus, distinct accessible action names, and reduced-motion support. Preserve Wi-Fi setup security and R34's short startup-window state reporting.

## Baseline, parent PR and anti-rollback
- Branched from **unmerged R34 PiBooter PR #44** `update/pibooter-0_1_4-onboarding-states`, NOT merged main, to preserve R34 failed-connection state and retry messaging. Review/merge R34 before this R35 PR.
- Inspected actual launcher `PiBooter/run_pibooter.py`, embedded `HTML_SHELL` in `pibooter/app.py`, Wi-Fi listing and forget action generators, GET `/api/status`, U19 CSRF/subnet/Origin checks and credential handling. Reviewed previous patch notes R34, 0_1_3 (U19), 0_1_2 (U16), 0_1_1 and initial 0_1_0.
- Preserve exact 5-second default, eligible-first-client session hold, auto-stop on no client, NetworkManager connection/hotspot handover, last saved router IP, private hotspot password, fail-closed provisioning, recovery copies, install/systemd runtime behavior. Never write persistent user config values from this UI patch.

## Root cause
The rendered Wi-Fi list repeated a generic **Use this network** button, and saved profiles each had an indistinguishable **Forget** label to a screen reader. There was no skip-to-main control, reduction of hardcoded smooth scroll, or forced-colors focus fallback. Keyboard focus visibility was incomplete for select/textarea controls. R34's progress messaging already used `role="status" aria-live="polite"`, so no additional high-frequency live announcements are needed.

## Files changed
- `PiBooter/pibooter/app.py`: add a focus-visible **Skip to setup** link and labelled main landmark (the existing forms and three CSRF fields stay intact). Use a prefixed accessible action name including a properly escaped SSID for each scanned network's **Use this network** button, and an escaped profile name for **Forget**. Preserve the visible short labels. Extend the focus-visible ring to all form controls, add forced-colors fallback and reduced-motion CSS, and honor `prefers-reduced-motion` when scrolling to a selected SSID. Increment existing HTTP server label `PiBooter/0.1.4` to `PiBooter/0.1.5`. No Wi-Fi command, backend session, setup-window or HTTP authorization change.
- `PiBooter/tests/test_accessibility_r35.cjs` (new): 14 deterministic V8 cases for HTML_SHELL formatting, inline browser script parse, skip link/main target, distinct action names, focus and low-motion semantics, preserved CSRF and startup safeguards; simulated `fillSsid()` scroll/focus in both motion-preference modes.
- `PiBooter/README.md`: keyboard-only setup guide and accessibility behavior.
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_5.md`: this note.

## User-visible behavior
Tab to scanned Wi-Fi choice, type or choose SSID, enter password, then activate the existing native Connect button. Choose Refresh scan or Clear password by keyboard. No new shortcut sends a connection mutation; the unchanged CSRF-protected form POST is still required. Screen-reader action names distinguish available networks and forget targets without printing any Wi-Fi or hotspot password. Users who prefer reduced motion do not get a smooth scroll animation; all other phone setup behavior remains unchanged.

## Verification actually performed
- **14/14** V8 tests executed from the exact connected GitHub branch files using a CommonJS-compatible adapter.
- The generated HTML shell's placeholders/doubled JS braces were expanded; full inline browser JavaScript parsed. A simulated DOM verified reduced-motion scrolling and focus behavior.
- Source checks confirmed prior R34 status projection, GET/POST security gates, original auto-exit threshold and that no private hotspot password enters the HTML shell.
- GitHub comparison of this branch against R34 checked for component-only, forward changes (detailed in PR).
- **Not performed:** Python compile, existing U19/R34 HTTP/Python test suites, Raspberry Pi NetworkManager or real phone/browser/screen-reader test. No hotspot credential is transmitted in this verification.

## Known limits
Screen readers and mobile keyboard behavior can vary; verify with hardware/browser. Physical hotspot session lifetime remains short by design and is unaffected by focus/scroll. NetworkManager still receives Wi-Fi credentials through its existing local command invocation; this patch does not address local process inspection.
