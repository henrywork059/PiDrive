# PATCH NOTES — PiBooter_0_1_3: secure hotspot onboarding (U19)

## Request summary
Implement roadmap U19, improve default Wi-Fi hotspot provisioning and limit unauthorized network-changing operations without changing the accepted short first-client setup workflow. This patch builds forward on pending PiBooter PR #10 (`0_1_2` configuration recovery).

## Root cause
PiBooter included a publicly known WPA2 hotspot password in its checked-in settings. The old setup page exposed the password in HTML and JSON, while POST `/connect`, `/forget` and `/rescan` had no request-token or client-network checks. GET `/api/networks` also triggered active Wi-Fi scans; SSIDs were inserted in inline handlers without HTML attribute quote escaping.

## Baseline and anti-rollback
- Verified live GitHub PR #10's `app.py`, `config.py` and tests against the uploaded PiBooter 0_1_2 patch using exact Git blob SHA values.
- Reviewed available component notes `0_1_2`, `0_1_1` and `0_1_0`.
- Preserve the five-second startup first-client window, session hold, Wi-Fi connection/recovery, saved router IP, status file, and systemd `Restart=on-failure` behavior.
- Preserve 0_1_2's non-destructive recovery copies and refusal to overwrite malformed settings.
- Existing custom hotspot passwords, unknown config keys, and existing Wi-Fi connections are never silently reset or rotated. No persistent user configuration file is included in this patch.

## Files changed
- `PiBooter/pibooter/provisioning_security.py` — new
- `PiBooter/pibooter/config.py`
- `PiBooter/pibooter/network.py`
- `PiBooter/pibooter/app.py`
- `PiBooter/install.sh`
- `PiBooter/README.md`
- `PiBooter/tests/test_provisioning_security.py` — new
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_3.md` — new

## Exact behavior
1. A missing configuration receives a cryptographically random, unique per-device WPA passphrase using `secrets.token_urlsafe(24)`. It persists unchanged on subsequent launches. A configured custom passphrase is retained.
2. The **published legacy default is not silently changed during normal boot**. An explicit `--provision-hotspot-password` command, also invoked by `install.sh`, replaces it with a private value while preserving other keys. `--rotate-hotspot-password` explicitly changes any existing password; `--show-hotspot-password` prints the secret only when requested locally.
3. The NetworkManager adapter refuses to create or start a hotspot with the known public password or invalid WPA length before issuing an nmcli command. The controller also attempts to shut down any already-active hotspot using that credential and displays a clear diagnostic.
4. Setup mutations (`/connect`, `/forget`, `/rescan`) require a session-lifetime CSRF form token, a client address inside the configured setup subnet or local loopback, and a matching HTTP Origin when supplied. Bounded request bodies and safe parsing reject malformed/oversized requests.
5. The three HTML setup forms supply the CSRF token automatically. Off-hotspot web probes cannot extend the five-second first-client window; legitimate hotspot clients and local operators still can.
6. The hotspot password no longer appears in page content, the in-memory web-status payload, or `/api/status`. The installer displays it only when output goes to a terminal; noninteractive logs contain only instructions to retrieve it locally. Install-time config permissions are set to 0600.
7. GET `/api/networks` reads the cached results without triggering an active rescan. POST `/rescan` remains functional with request protection.
8. Scanned SSIDs are HTML-quote-escaped before inclusion in JavaScript handler attributes to prevent markup injection. HTTP responses use no-store, nosniff, no-referrer, and deny-frame headers.
9. The HTTP server version string is updated to `PiBooter/0.1.3`; file structure, stable paths and persistent JSON schema remain unchanged. The service restart runs after the operator has been shown the credential in the installer.

## Verification actually performed
Locally assembled the latest GitHub-compatible 0_1_2 tree from `PiDrive-main.zip` and the uploaded 0_1_2 patch, verifying changed source hashes match the live PR #10.
- `cd PiBooter && python -m unittest discover -s tests -q`: **18 tests passed** (existing config recovery tests plus provisioning and HTTP handler regression tests).
- `python -m compileall -q pibooter tests run_pibooter.py`: passed.
- `bash -n install.sh`: passed.
- Tests exercise first-creation entropy, persistent password, no silent rotation, manual override, corrupt config refusal, backend rejecting the default, attempted shutdown of an active legacy hotspot, client address constraints, Origin/CSRF validation, actual localhost HTTP forms, no password in UI/API, safe SSIDs, GET without rescan, and rejected oversize/malformed requests.

## Known limits / next steps
- Real Raspberry Pi, NetworkManager, hotspot/phone and five-second onboarding tests were **not** performed. Verify those on hardware before merging/deploying.
- This is a WPA hotspot possession + request-token model, not an additional user account login. A connected hotspot client can fetch its own request token. Plain HTTP is unencrypted; **do not expose this port to the Internet**.
- A previously active weak hotspot may not stop if the underlying nmcli shutdown fails; inspect actual NetworkManager status and test fail-closed behavior on the Pi.
- NetworkManager still receives Wi-Fi credentials via local command arguments; avoiding their appearance in process inspection requires a separate improvement.
- The installer intentionally modifies the Pi's local tracked settings file. Never commit the provisioned password to the public repository.
- Merge/review PR #10 first; then review this stacked change. No unrelated component was modified.
