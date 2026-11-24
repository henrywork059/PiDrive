# PiBooter 0_1_4 — R34 explicit onboarding status and safe recovery

## Request
Implement roadmap **R34 — PiBooter onboarding clarity**: explicitly distinguish scanning nearby Wi-Fi, connecting, connected, failed, and closing startup window; give context-sensitive next steps without exposing passwords, silently extending hotspot uptime, or obscuring the short first-client exit rule.

## Baseline and anti-rollback review
- Exact live baseline: merged GitHub `main` commit `c615c73032d62daa23ec0fe302d1cfe6049428c3`. The independent CustomDrive R33 PR #43 remains open and is **not** a PiBooter dependency.
- Verified the actual entry point `PiBooter/run_pibooter.py` → `pibooter.app.main()` → `PiBooterController`; reviewed the current `HTML_SHELL`, `render_index_body`, GET `/api/status`, `/rescan` and `/connect`, `network.py`, `state.py`, and existing U19 provisioning tests.
- Reviewed prior component notes `PATCH_NOTES_PiBooter_0_1_3`, `0_1_2`, `0_1_1` and `0_1_0` for startup/window, password protection, config recovery and existing scan/connection behavior.
- Preserve default **5-second** `server.startup_wait_s`, first eligible client session hold, `_monitor_loop` shutdown/stop_hotspot behavior, success IP persistence and exit, U19 setup-token/subnet/Origin checks and password isolation, U16 non-destructive config recovery, installer and service `Restart=on-failure`. No config file or saved password is changed.

## Root cause
The legacy page's status pill mirrored `network.phase`, often `hotspot` after a failed connection, while the actual failed attempt was stored separately in `connection_attempt`. Users could be left seeing a restored hotspot rather than a specific safe retry action. The first-client countdown displayed `Locked second(s)` when the setup session had been activated; near expiry it did not explicitly explain the impending automatic shutdown. A rescan offered no immediate visible status. Finally, raw `nmcli` error output was surfaced in connection failure logs and notices, potentially including a password echoed by the command tool.

## Changed paths
- `PiBooter/pibooter/onboarding_status.py` (**new**): pure, read-only `project_onboarding(snapshot)` giving bounded credential-free `state`, `headline`, `summary`, `next_action`, `session_active`, `startup_remaining_s`, `retry_available` and `scan_in_progress`. States: `scanning`, `connecting`, `connected`, `failed`, `window_closing`, `ready`, `starting`.
- `PiBooter/pibooter/app.py`: return additive `onboarding` object in existing GET `/api/status`; render identical initial step/action in server HTML and update it through existing polling (no new timer). Mark a POST `/rescan` as scan-in-progress during the already-existing synchronous operation, resetting it even on exceptions. The existing scan and connect forms give immediate, read-only submitted-step feedback. Explicitly label closing startup window without changing the timer. Unexpected NetworkManager errors now produce the same recoverable failure state, instead of leaving the attempt at `running`. Classify raw nmcli failures into safe authentication/network-not-found/timeout/general messages **without publishing raw command stderr or passwords**. Server version label `PiBooter/0.1.3` → `PiBooter/0.1.4`.
- `PiBooter/tests/test_onboarding_status.py` (**new**): 24 hardware-free tests for state precedence, real session countdown, successful handover, failed hotspot recovery, sensitive status exclusion, markup escaping, all original CSRF form fields, in-flight rescan cleanup, safe failure classifications, and unexpected exception handling.
- `PiBooter/README.md`: document exact state meanings, safe recovery, and existing `run_pibooter.py` commands.
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_4.md` (**new**): this note.

## Exact behavior and security
- When `connection_attempt.status` is `running`, `success`, or `error`, it takes precedence over the NetworkManager background phase; an error is not overwritten by a restored hotspot. In a failed attempt, users are told to rejoin the setup hotspot (if still available) and re-enter SSID/password, or restart PiBooter locally if the hotspot did not return.
- `window_closing` appears only when the first-client session is **not** active and the original remaining time reaches two seconds (or shutdown has been requested). The read-only projection **never calls `_activate_session`, never lengthens a deadline, never starts a hotspot**, and preserves the original monitor shutdown. Polling the status page follows the preexisting interval and cannot by itself grant a setup session from an unauthorized off-subnet address.
- `scanning` is tied to an actual force-rescan request; the UI also acknowledges the form submission immediately. A missing SSID can be typed manually; no fictitious scan result is added.
- Successful connection retains the existing last-known router IP and service exit, and reminds the operator to switch the phone back to the router network. The saved address is explicitly *last known*.
- The UI does not display the configured private hotspot password, the submitted Wi-Fi password, raw nmcli failure details or CSRF tokens beyond the existing secured hidden inputs. Existing form POST authorization is unchanged.

## Verification performed
- Fetched exact final branch `app.py` and extracted its embedded HTML shell. Confirmed all Python-style HTML escaping tokens/placeholders are recognized, expanded the double-braced CSS/JS delimiters, and **parsed the resulting full inline browser script successfully in V8**. Checked scan/connection form listeners, status projection rendering and existing security token route source.
- Source-level comparison against `main` to verify no unexpected component files or deletions; outcome reported in the draft PR.
- The 24 new Python tests were added and inspected but **not executed** in the connected GitHub environment; full Python compilation, PiBooter HTTP integration, hardware NetworkManager, live 5-second phone join and unsafe credential handover tests **were not run**.

## Limits / next steps
- The five-second timer is intentionally short: depending on actual phone radio timing, the closing state may not be observed before the service exits. It does not guarantee the phone can join in time.
- The visible network error is now a safe category, not raw `nmcli` stderr; developers needing the complete original failure must debug NetworkManager locally with privileged tooling and keep credentials private.
- The service still uses plain HTTP over the isolated setup hotspot; as noted in U19, NetworkManager may receive credentials in local process arguments. This patch does not claim to fix local process inspection.
- Validate on a Raspberry Pi/NetworkManager and run `cd PiBooter && python3 -m unittest discover -s tests -v` before promoting the draft PR. Test the original no-client auto-exit, client-hold, failed join and hotspot restore, terminal success exit, and corruption recovery paths.
