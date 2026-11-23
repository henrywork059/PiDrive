# PiBooter 0_1_6 — R36 mobile Wi-Fi selection reachability

## Request
Implement the R36 responsive verification subset for PiBooter setup, focusing on the 390/768/1024/1440 px matrix and ensuring primary Wi-Fi actions remain discoverable and touch/keyboard-reachable without changing network provisioning.

## Baseline and anti-rollback
- Based on unmerged R35 PiBooter PR #48 (`update/pibooter-0_1_5-accessibility-parity`) which is stacked on R34 PR #44. **Review/merge #44, then #48, before this R36 patch.**
- Inspected `PiBooter/run_pibooter.py` → `pibooter.app.main()`, actual HTML_SHELL and the network scan/known-profile row generators, current R35, R34, 0_1_3 and 0_1_2 patch notes.
- Preserve U19 protected hotspot password and token/Origin/subnet checks, U16 config recovery, R34 visible failure stages and unchanged default five-second first-client window, R35 keyboard named actions/reduced motion.

## Root cause — confirmed source defect
The generic mobile media query at ≤640 px used `th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5) {display:none}` for **every** table. In the nearby Wi-Fi scan table, **column five holds the `Use this network` button**. At the required 390 px, this rule hid the primary scanned network selection action, despite the source generating it properly. Wide saved profiles could also expand a narrow card.

## Exact files and behavior
- `PiBooter/pibooter/app.py`: scope mobile column hiding to the fourth **device connection** and fourth **scan channel** columns only; preserve the fifth scan action cell and sticky-position it on the right of its own scrollable table at ≤640 px. Add labelled keyboard-focusable horizontal scroll wrappers for scanned SSIDs and saved-profile tables, with text wrapping and 44 px minimum target height. Use overflow-safe CSS grid tracks and page card min-width; leave form action URLs, CSRF tokens, network commands, session policy and credentials untouched. Advance existing server marker **PiBooter/0.1.5 → PiBooter/0.1.6**.
- `PiBooter/tests/test_responsive_r36.cjs` (new): 12 source-level cases for the fifth action visibility regression, scrolling, existing CSRF and five-second shutdown condition, version and no password in HTML shell.
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_6.md`: this note.

## Required viewport matrix
| Width | Scan action and saved-profile Forget | Connection and next-action guidance | Screenshots |
|---|---|---|---|
| 390 | Fifth column now visible / sticky in a horizontally-scrollable region | Check form buttons and input widths | Pending live |
| 768 | Desktop table columns remain displayed | Check setup/scan grid wraps | Pending live |
| 1024 | All columns normally displayed | Check forms | Pending live |
| 1440 | Max-width card retained | Check forms | Pending live |

Screenshot runner: `PiServer/tests/capture_responsive_r36.py --suite pibooter --acknowledge-booter-visit --url <authorized-url> ...` (in PiServer R36 PR). A real PiBooter page GET from a permitted client **may activate the existing first-client setup session**; only run this against authorized test equipment. The runner never submits new Wi-Fi commands, but some optional network action checks require a safely pre-populated scan/profile fixture. Full matrix: `PiServer/tests/R36_VIEWPORT_MATRIX.md`.

## Verification actually performed
- **12/12** source-level mobile action regressions passed in V8 against exact connected GitHub branch source.
- Reviewed original and patched mobile selectors and the scanned/saved row builders.
- GitHub component-only compare against R35 parent checked in PR.
- **Not performed:** actual PiBooter Python compile/HTTP test, NetworkManager, full Playwright browser capture, real phone selection or restart, Wi-Fi password transmission, 4-width screenshot diff.

## Limitations / merge gate
Sticky action cells need a real phone/touch and keyboard pass, including a long SSID and saved profile. Do not assert R36 visually complete until the baseline and patched snapshots have been captured and inspected. Keep the original short setup window, password secrecy and test network isolated.
