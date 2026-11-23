# CustomDrive R35 — accessible keyboard input, hold-action release and Mission 1 announcements

## Request summary
Implement roadmap R35 across the existing CustomDrive GUI web runtime and Mission 1 viewer: accessible focus and input names, non-motor keyboard navigation, reduced-motion styling, and an accessible stop alternative. Hardware motor and servo actions must remain subject to existing backend safety and must not be newly authorized by the UI.

## Exact baseline and latest notes
- Branched from **unmerged CustomDrive R33 PR #43**, `update/customdrive-r33-mission-timeline`, not main. The parent already contains the R33 Mission 1 stage timeline. This branch must be reviewed/merged **after PR #43**.
- Inspected `CustomDrive/run_custom_drive_gui.py` / `run_custom_drive_web.py`, actual GUI web `custom_drive/gui_web/`, Mission 1 `custom_drive/mission1_session_app.py` / `mission1_web/`, and prior component patch notes R33, R31, R30, U29, and 0_5_20 (U28). Preserve all live GUI runtime settings, R31 backend-verified Save/Retry, R30 camera freshness, U28 stop/rearm, R33 timeline, mission control, arm and motor backends.

## Root cause
The GUI's servo hold buttons were only wired for pointerdown and pointerup, so a keyboard user could focus the buttons but Enter/Space would not start or stop the held action. The manual drive pad is intentionally pointer-operated and had no nearby accessible emergency zeroing alternative. The settings modals were displayed without dialog roles or reliable focus return/trapping. CSS lacked a consistent visible-focus and reduced-motion layer. R33's Mission 1 current-stage strong element was live-announced even as the entire timeline DOM was recreated on repeated status refreshes, risking repetitive screen-reader announcements.

## Changed files and exact behavior
- `CustomDrive/custom_drive/gui_web/static/app.js` — reuse the same `/api/arm/action` endpoints for Space/Enter press-and-release on six existing servo/gripper hold buttons. Ignore key repeats. Request STOP on keyup, control blur, window blur and hidden page; sequence a rapid release's STOP **after** an in-flight start request so an asynchronous late start cannot override a previous stop. Preserve existing pointer behavior and the backend authorization checks. New non-motor dialog keyboard controller: Escape closes, Tab and Shift+Tab remain inside the visible modal, close restores the opener focus. The existing manual pad is *not* assigned new movement keyboard shortcuts; an explicit button calls the already-existing `releaseDrivePad()` zeroing method, also called on page blur/hidden.
- `CustomDrive/custom_drive/gui_web/templates/index.html` — three named `role="dialog"` / `aria-modal` windows; meaningful status regions; pointer pad `role="group"` with a static description of its pointer-only behavior and the keyboard-usable **STOP manual output** button.
- `CustomDrive/custom_drive/gui_web/static/styles.css` — high-contrast focus outlines including E-Stop toggle's wrapping label, disabled-motion styles and forced-colors fallback. No existing theme/docking layout reset.
- `CustomDrive/custom_drive/mission1_web/static/app.js` — announce mission step/outcome/failure changes only when their values change, through a persistent live region separate from the R33 periodically re-rendered timeline. Do not send motor commands.
- `CustomDrive/custom_drive/mission1_web/templates/index.html` — add visually hidden `missionTimelineAnnouncement` `role="status"`, `aria-live="polite"`, `aria-atomic="true"` before R33 timeline.
- `CustomDrive/custom_drive/mission1_web/static/styles.css` — corresponding visually hidden helper and shared focus/reduced-motion styles; preserve timeline visuals and stage semantics.
- `CustomDrive/custom_drive/gui_control_app.py` — existing GUI asset version **0_3_12 → 0_3_13**.
- `CustomDrive/custom_drive/mission1_session_app.py` — existing Mission 1 asset version **0_5_21 → 0_5_22**.
- `CustomDrive/tests/test_accessibility_r35.cjs` (new) — 14 simulated keyboard/arm hold, modal markup, manual STOP and Mission 1 announcement-source regression checks.
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R35.md` — this note.

## Hardware safety boundary
This patch does not implement arbitrary keyboard movement of physical motors. A keyboard user can reach and activate the non-driving setup controls and the dedicated manual STOP, while actual pad movement remains pointer-driven pending separate hardware safety validation. The added servo key handlers use the exact same existing POST start/stop actions as pointer input and never bypass motor/arm authorization. Quick key release orders STOP behind an uncompleted START request; on lost focus/visibility it still issues STOP. Existing server-side watchdogs and E-Stop remain authoritative.

## Verification actually performed
- **14/14** deterministic V8 tests executed against the final GitHub branch's GUI JS/HTML/CSS and Mission 1 JS/HTML/CSS, including Space/Enter start and stop, repeated-key suppression, focus-loss STOP, and a delayed START followed by quick STOP.
- Full GUI and Mission 1 browser scripts parsed in V8.
- Examined the preserved backend control and mission paths and compared this branch against R33 parent for component-only changes.
- **Not performed:** actual Node subprocess, Python/Flask integration, real Raspberry Pi servo/GPIO, physical motor permission testing, touch/keyboard real-browser operation or assistive-technology testing.

## Limitations / next steps
Network disconnect may prevent a client-side STOP packet from reaching the Pi; the existing backend deadman/authorization remains essential. Returning focus to an opener depends on the opener still being mounted. Hardware servo safety, grip confirmation and active mission rearm are not changed by these accessibility additions. Verify on the Pi with servo power disconnected initially, normal touch/pointer movement, and all E-Stop/fault paths before promotion.
