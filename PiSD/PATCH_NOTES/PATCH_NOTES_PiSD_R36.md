# PiSD 0.11.17 — R36 responsive layout verification and minimal safeguards

## Request and acceptance
Implement R36: a real 390/768/1024/1440 px viewport checklist for Manual Drive and AI Mode, with camera aspect, square drag pad, scrolling, popup Apply and emergency STOP. **This patch is not a screenshot sign-off**: current live backend browser captures and baseline/patched image comparisons remain pending.

## Exact baseline / anti-rollback
- Based on R35 PR #45 head `update/pisd-r35-accessibility-parity`, not outdated uploaded PiDrive ZIP or `main`.
- Compared actual current files and reviewed latest component patch notes R35 (Space/native control handling), R32 (readiness), R31 (confirmed settings) and U29 (safe replay). Verified actual entry `PiSD/PiSD.py` (defaults localhost port 5050).
- Preserve R35 keyboard STOP and focus styles, R32 model/camera status strip, R31 settings and retries, U29 replay, U28 camera stale latch and motor authorization, drag pad shape, saved UI preferences, records/captures, and overlay.

## Root cause
The small-screen layout already has 390/768/1024 breakpoints and preserves a 1:1 manual pad and a 16:9 live preview. The remaining vulnerable elements are long, safety-critical STOP text and footer actions inside compact viewport-width/viewport-height settings popups. At 390 px with customized font/button scale, overflowing labels or a fixed-height popup can hide Apply/Stop. A broad layout rewrite would risk regressing the working semantic grid order and presets.

## Changed files
- `PiSD/pisd/web/static/css/pisd_layout_system.css`: *add-only* phone-width rules for the existing STOP buttons on Manual/AI modes: 44 px minimum height, wrapping text, max-width within viewport. Existing `mdrv-actions` and overlay-popup actions can wrap; settings popup card gains dynamic viewport max height and internal vertical scroll. Does not alter drag-pad geometry, camera aspect, panel placement or saved overrides.
- `PiSD/pisd/__init__.py`: advance existing patch version **0.11.16 → 0.11.17** for asset cache.
- `PiSD/scripts/test_responsive_r36.cjs`: 11 static regression checks for existing 1:1 pad, aspect-aware camera, semantic order, STOP controls, mobile popup, R35 focus and version.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R36.md`: this note.

## Required viewport matrix
| Width | Manual STOP / drag pad / preview / popup Apply | AI STOP / model Save / preview / workflow Apply | Status |
|---|---|---|---|
| 390 px | Current source guarded, screenshot pending | Current source guarded, screenshot pending | **PENDING visual** |
| 768 px | Verify stacked/2-column transition, popup scroll | Verify AI panel scrolling | **PENDING visual** |
| 1024 px | Verify grid sizing and camera ratio | Verify preview/control coexistence | **PENDING visual** |
| 1440 px | Verify existing two-column layout and saved settings | Verify wide AI preview | **PENDING visual** |

Use the shared passive Playwright capture/geometry tool in `PiServer/tests/capture_responsive_r36.py` with suites `pisd-manual` and `pisd-ai` against real endpoints `/manual-drive` and `/ai-mode`, first on R35 parent for baseline and then R36 for patched. Full matrix/instructions: `PiServer/tests/R36_VIEWPORT_MATRIX.md` (in the corresponding PiServer R36 PR).

## Verification actually performed
- **11/11** source-level R36 tests passed in V8 CommonJS-compatible harness using exact GitHub branch contents.
- GitHub compare against R35 parent checked component-only changes, no deletions or rollback (see draft PR).
- **Not run**: live PiSD Flask app, Python/Flask, physical camera/motor, 4-width browser screenshots, screenshot image diff, real touch/keyboard/low-height popup usability.

## Limits and release gate
Layout assertions are *source checks*, not computed-style measurements. Do not merge R36 as visually complete until latest parent and patched live versions have been captured at all four widths, image differences inspected, and STOP/Apply controls confirmed reachable. Do not bypass hardware safety for test screenshots.
