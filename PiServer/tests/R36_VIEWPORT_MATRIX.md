# R36 — Responsive viewport screenshot and reachability matrix

## Status at patch creation
**Source-verified and patched, not visually signed off.** The connected GitHub
branches are accessible in this environment, but their running Flask/phone
web servers are not. No current-baseline or patched screenshots of the live
pages have been captured yet. Do NOT claim screenshot comparisons have passed.
The source-level R36 tests passed: PiSD 11/11, PiServer 12/12,
CustomDrive 14/14 and PiBooter 12/12 (49/49 combined). Those checks cannot
replace browser layout measurements and a real keyboard/touch review.

## Required viewport matrix (all pending real-browser verification)

| Page/suite | 390×844 | 768×1024 | 1024×768 | 1440×900 | Must check |
|---|---|---|---|---|---|
| PiSD Manual Drive | Pending | Pending | Pending | Pending | STOP top/pad/full, square drag pad, 16:9 preview, visual settings Apply and page scroll |
| PiSD AI Mode | Pending | Pending | Pending | Pending | STOP AI/motors, model Save, preview, workflow settings Apply |
| PiServer workspace | Pending | Pending | Pending | Pending | E-Stop, exact square resize-pad, Save tuning, style modal Save, dock scrolling |
| CustomDrive GUI | Pending | Pending | Pending | Pending | visible toolbar, E-Stop/manual STOP, square pointer pad, Drive settings Save |
| CustomDrive Mission 1 | Pending | Pending | Pending | Pending | STOP, Save config, 16:9 camera, arm table horizontal scrolling, R33 timeline |
| PiBooter setup | Pending | Pending | Pending | Pending | Connect, **Use this network** in 5th scan column, Forget, next-action guidance |

**Baseline and patched** screenshots must be captured for each width after
checking out the corresponding parent/new branch and running its real
application. The CLI writes `<suite>_<width>.png`, optional
`<suite>_<width>_dialog.png`, and a `matrix.json` with geometry checks.
A missing required control, horizontally clipped action, non-square drive
pad or unreachable Save is reported as an error.

## Screenshot runner (desktop-only development dependency)

```bash
python -m pip install playwright
python -m playwright install chromium

# Start the actual web app via the verified component launcher separately.
# Then point this passive browser checker at the live URL. Never click motors.
python PiServer/tests/capture_responsive_r36.py \
  --suite piserver --url http://127.0.0.1:5000/ \
  --label baseline --revision YOUR_PARENT_SHA --output ./r36_screenshots

# Switch to the R36 branch and restart that SAME runtime, then:
python PiServer/tests/capture_responsive_r36.py \
  --suite piserver --url http://127.0.0.1:5000/ \
  --label patched --revision YOUR_R36_SHA --output ./r36_screenshots \
  --baseline-dir ./r36_screenshots/piserver/baseline
```

Run these **exact supported suites**, changing URL/port to the actual running
service (do not guess a mission or PiBooter URL):

```text
--suite pisd-manual           --url http://127.0.0.1:5050/manual-drive
--suite pisd-ai               --url http://127.0.0.1:5050/ai-mode
--suite piserver              --url http://127.0.0.1:5000/
--suite customdrive-gui       --url http://127.0.0.1:<GUI-PORT>/
--suite customdrive-mission1  --url http://127.0.0.1:<MISSION1-PORT>/
--suite pibooter              --url http://<AUTHORIZED-SETUP-IP>/
```

Verified launch entry points:
- PiSD: `PiSD/PiSD.py` (local simulation default port 5050).
- PiServer: `PiServer/server.py` (environment `PISERVER_PORT`, default 5000;
  access controls may require authentication).
- CustomDrive GUI: `CustomDrive/run_custom_drive_web.py` (the
  `run_custom_drive_gui.py` entry forwards here; actual port comes from
  `CustomDrive/config/manual_control.json` unless overridden).
- CustomDrive Mission 1: `CustomDrive/run_mission1_stage_test_demo.py`
  (port from `CustomDrive/config/mission1_session.json` unless overridden).
- PiBooter: `PiBooter/run_pibooter.py` (local configured port, short first-client
  setup window). A missing scan/profile means the relevant optional buttons
  cannot be validated. Do not trigger an unauthorized scan or extend the
  five-second window to make a test easier.

## Acceptance review procedure
1. Capture **baseline** screenshots from each parent branch, not the older
   uploaded zip. The attached historical ZIP is **not** the current source.
2. Capture **patched** screenshots from the R36 branches; capture Save dialog
   after it opens, with the Save button scrolled into view.
3. Inspect both sets side-by-side at 390, 768, 1024 and 1440: compare STOP
   labels, model/config Save, 16:9 camera shape, 1:1 drag pad, horizontal scroll,
   modal viewport fit, thumb reach and preserved docking.
4. Inspect `matrix.json`. All required controls must be visible/reachable,
   no unintended horizontal page overflow, no clipped STOP/Save labels,
   and no distortion of the resizable PiServer square drag pad.
5. Recheck at least one phone in touch mode and one keyboard-only pass, without
   sending a motor drive command. Hardware motion actions require a separate
   authorized safety review.
6. Screenshot files may contain camera views, private Wi-Fi SSIDs and local IPs:
   **do not commit raw captures** until reviewed and redacted.

The runner is a passive capture and reachability utility. It does not issue
Wi-Fi `/rescan`, `/connect`, motor, servo, mission, Save or STOP API commands.
Opening a local settings panel is a presentation-only operation; verify this
assumption for the actual running version.

**Merge gate:** Every R36 PR remains **draft** pending the real-browser
baseline/patch screenshot review. Source-only checks are not a sign-off.
