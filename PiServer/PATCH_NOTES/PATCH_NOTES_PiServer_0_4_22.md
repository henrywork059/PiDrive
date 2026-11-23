# PiServer 0_4_22 — R36 responsive verification, popup reachability and passive screenshot matrix

## Request and acceptance
Build the R36 four-width baseline/patch verification matrix, applying the smallest responsive CSS changes that keep safety labels and style Save reachable. **Do not redesign docking**; the resizable square manual pad and user layout preferences are accepted behavior. Real screenshots and visual review are **PENDING**, not silently marked passed.

## Exact baseline and prior notes
- Based on unmerged R35 PiServer PR #46 `update/piserver-0_4_21-accessibility-parity`, not the old ZIP or main.
- Reviewed actual `PiServer/server.py` (host selected by access policy; `PISERVER_PORT` default 5000), latest R35 notes 0_4_21, prior R31 0_4_20, R30 0_4_19 and U28 0_4_18.
- Preserve user saved themes/docking, manual pad sizing and panel resizers, R31 motor/camera persistence, R30 preview freshness, R35 keyboard focus/labelled tabs/style dialog and U28 safety latch/authorization.

## Root cause
The existing mobile layout already switches to stacked panels, and the style dialog has a scrollable body. Under a 390 px phone width or constrained landscape height, fixed modal margins and a non-wrapping header/footer could make Save labels/Save actions hard to access. E-Stop labels also need to wrap without affecting motor logic. No change is needed to the square pad's existing JS sizing and docking.

## Files changed
- `PiServer/piserver/web/static/styles.css`: phone-only (≤760 px) dialog sizing uses a safe 8 px gutter and dynamic viewport max-height; modal body uses a flex-child internal scrollbar, while its header/footer stay accessible and can wrap. STOP/Save labels wrap inside their existing buttons. No change to `joystick-area`, resize handles or workspace docking.
- `PiServer/piserver/app.py`: advance established version marker **0_4_21 → 0_4_22**.
- `PiServer/tests/capture_responsive_r36.py` (new): generic passive Playwright screenshot/geometry auditor for **six current page suites** across 390×844, 768×1024, 1024×768, 1440×900. Captures PNGs and `matrix.json`; checks required STOP/Save, horizontal overflow, square pad and preview ratios, dialog Save reachability. It does not directly issue control POSTs. Visiting PiBooter may activate an authorized setup session and therefore requires `--acknowledge-booter-visit`.
- `PiServer/tests/R36_VIEWPORT_MATRIX.md` (new): exact suite selectors, verified launcher commands, full viewport matrix, baseline/patch screenshot procedure, privacy and merge gate.
- `PiServer/tests/test_responsive_r36.cjs` (new): 12 deterministic source checks for pad geometry, dialog scroll/Save, focus and screenshot tool.
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_22.md`: this note.

## Required viewport matrix
| Width | E-Stop and Save tuning | Existing square pad/docking | Style dialog Save | Baseline/patched screenshots |
|---|---|---|---|---|
| 390 px | Source guarded; on-device check pending | **Do not resize rectangularly** | Scrollable, visual check pending | Pending |
| 768 px | Source guarded; check pending | Stacked layout expected | Scrollable, check pending | Pending |
| 1024 px | Source guarded; check pending | Existing medium-screen stack | Normal dialog | Pending |
| 1440 px | Source guarded; check pending | Existing desktop docking | Normal dialog | Pending |

Use the exact commands in `tests/R36_VIEWPORT_MATRIX.md`. Screenshot folders may contain private camera/IP information; keep them uncommitted/unshared without review.

## Verification actually performed
- **12/12** source-level tests executed in V8 against exact GitHub branch files.
- Actual source inspected for expected selectors; current CSS version and launch file verified.
- GitHub compare against R35 parent for file changes, no deletions/rollback in PR.
- **Not run:** the new full Playwright capture runner against live PiServer pages, Python script compilation in the connected GitHub context, baseline/patch PNG comparison, authenticated Flask suite, Raspberry Pi camera/motor or phone/browser manual tests.

## Limits / merge gate
A static selector check cannot prove computed mobile geometry. Keep this PR a draft until the browser screenshot matrix and physical/keyboard critical-action checks are reviewed. The screenshot tool never presses an E-Stop or Save API, so operator verification still has to check those controls work safely.
