# PATCH NOTES — PiBooter 0_1_2

## Request summary
Implement **U16**, non-destructive configuration recovery, as an independent PiBooter roadmap patch. Improve the phone UI's reporting of configuration errors without changing the Wi-Fi setup flow.

## Baseline and rollback checks
- Verified current GitHub PiBooter source against `PiDrive-main.zip` and reviewed `PATCH_NOTES_PiBooter_0_1_0.md` and `PATCH_NOTES_PiBooter_0_1_1.md` (only two existing notes).
- Preserve the 5-second startup wait, first-client hold, NetworkManager flow, saved router IP, status file location, and systemd `Restart=on-failure` behavior.
- No runtime/config JSON values or Wi-Fi credentials are changed in the checked-in project.

## Root cause
`ConfigStore.load()` silently swallowed JSON parse failures and **always rewrote** `config/settings.json` with defaults, erasing the operator's original file. Invalid section types could also fail during normalization. Writes were not atomic.

## Files changed
- `PiBooter/pibooter/config.py`
- `PiBooter/pibooter/app.py`
- `PiBooter/README.md`
- `PiBooter/tests/test_config.py` (new)
- `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_2.md` (new)

## Exact behavior changes
1. Invalid JSON, invalid top-level structure and invalid object sections use in-memory defaults **without altering the original file**.
2. A best-effort recovery copy named `settings.json.corrupt-<content hash>` is created beside the original; repeated starts reuse the same copy. Recovery-copy failures are reported rather than silently deleting/overwriting data.
3. `ConfigStore.save()` refuses to replace a corrupt original by default; explicit `replace_invalid=True` is required after manual recovery decision.
4. Valid configuration merges preserve unknown keys, credentials, and backward-compatible defaults. Normalization writes only when data changes, using a flushed, atomic replace with a temporary file.
5. The web page and runtime log show a clear, escaped recovery error if the config is invalid; `--write-default-config` exits with an error rather than silently reporting it overwrote a broken configuration.
6. README explains how to repair the original, review the backup and recover safely.

## Verification actually performed
- `python -m unittest discover -s tests -q` → **4 tests passed** locally.
- `python -m compileall -q pibooter tests run_pibooter.py` → passed.
- Tests cover malformed JSON, wrong schema, backups, explicit overwrite protection, existing credentials and unknown keys, repeated loads, and initial config creation.

## Known limits
- No Raspberry Pi Wi-Fi/hotspot or phone/browser test was performed.
- If the disk is read-only/full, backup creation may fail; the original file is still not intentionally modified and the runtime reports the condition.
- New-device hotspot credential hardening (**U19**) is separate and not implemented by this patch.
