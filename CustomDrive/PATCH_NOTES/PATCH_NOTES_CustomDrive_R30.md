# CustomDrive GUI R30 — Camera preview freshness and recovery

## Request / root cause
The GUI's previous <img> refresh loop treated each browser load event as a fresh camera frame even if PiServer's camera adapter served the same cached JPEG, and a failed camera could cause the status handler to disable subsequent polling. Add unambiguous Live / Delayed / Disconnected and age, preserved stale image, and automatic bounded retry without touching the mission controller or motor pipeline.

## Source and anti-rollback
Based directly on **CustomDrive U29 draft PR #36** `update/customdrive-u29-mission-replay` at `1179ffcbf8b688e0c21f28ad8f91e1250c78b981`. Reviewed patch notes U29, 0_5_20, 0_5_19, 0_5_18 (and 0_5_17). Preserves U29 read-only fake-robot mission replay; U28 standalone/Mission 1 safety rearm; U23 telemetry; U22 Mission 1 failure/arm checks; U24 trigger overlays; AI detection overlay and tuning, manual pad, save settings and existing web/GUI/headless launchers. No PiServer files, shared config, motor, hardware lease or watchdog code changed.

## Files changed
- `CustomDrive/custom_drive/gui_control_app.py`: add JPEG response headers `X-Preview-Seq` and `X-Preview-Live`, preserving the existing payload, overlay, no-store headers and route; GUI cache version becomes 0_3_11 (continuing the GUI's own 0_3_10 line; no Mission 1 version promotion).
- `CustomDrive/custom_drive/gui_web/static/app.js`: fetch/decode verified unique JPEG, preserve old successful image, monotonic age, bounded reconnect with no manual restart, never confuse camera health with the user's preview-enabled preference.
- `CustomDrive/custom_drive/gui_web/static/preview_freshness.js` (new): standalone deterministic preview health state machine.
- `CustomDrive/custom_drive/gui_web/templates/index.html`: unobtrusive indicator and script.
- `CustomDrive/custom_drive/gui_web/static/styles.css`: stale-image dimming and status label.
- `CustomDrive/tests/test_preview_freshness.cjs` (new): 14 deterministic state tests.
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R30.md` (new).

## Exact behavior
The client measures age using `performance.now()`, the timestamp of the last successfully decoded **unique, backend-live JPEG sequence**. Under 1.5s with no failures is Live, 1.5–6s or recent frame errors is Delayed, >=6s or backend offline/no good frame is Disconnected. No empty response, repeated JPEG, backend placeholder or failed decode replaces the successful image or refreshes its timestamp. Stale images are dimmed and always labeled; recovery to a new JPEG automatically returns to Live and resets exponential backoff. Retry grows 250ms → 500ms → 1s → 2s → 4s max and the standard 160/220ms schedule resumes on recovery. Operator Preview toggle and visibility pausing remain; backend failure alone never sets operator previewEnabled=false. Existing manual motor logic and AI overlay code continue untouched.

## Verification
The draft PR reports JavaScript syntax and deterministic state-machine checks conducted against these staged source files. No full Flask/browser image decode, real camera stream, model inference, GPIO, arm, Raspberry Pi or Windows GUI tests were performed in this session.

## Limits
Sequence identifies new JPEG publication, not physical sensor acquisition. App can only detect a backend which falsely asserts live after no new published frames via the monotonically increasing age. Real Pi test must confirm failure/reconnection timing and load under AI overlay. U29 replay remains unrelated and unmodified.
