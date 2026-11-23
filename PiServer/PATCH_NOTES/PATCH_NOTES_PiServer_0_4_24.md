# PiServer 0_4_24 — R45 component-owned visual token contract and drift checks

## Request
Implement the PiServer portion of `docs/roadmaps/PiDrive_Refinement_Roadmap.md` **R45**. Document the existing compact operator UI spacing/density, semantic status colors, action labels and recommended future icon sizing, and introduce small tests for accidental token/API drift and persisted user style overrides. Avoid mass palette/layout changes, component sharing dependencies and config resets.

## Baseline and rollback review
- Stacked on **open draft R43 PiServer PR #59**, branch `update/piserver-0_4_23-r43-adaptive-polling`, head `d6f721ee8b0fdaea71c28568ab082a7c39580cac`. New branch `update/piserver-0_4_24-r45-style-contract`; do not branch from old main or merge before R43/R36/R35.
- Read existing `PiServer/server.py` entry, `piserver/app.py` and web static `theme.js`/`styles.css`, plus current README and actual tests. Reviewed latest notes `0_4_23` (R43 adaptive polling), previous three `0_4_22` (R36 mobile modal actions), `0_4_21` (R35 focus/keyboard), `0_4_20` (R31 applied settings). Inspected older `0_4_19` preview freshness/sequence context where relevant.
- Exact observed `piserver/web/static/theme.js` SHA is `ca185fec09e6f02ce402a1ce1493d0f8c0ff935c`, byte-identical with CustomDrive GUI `theme.js` on the live branch. Those are **two component-owned files**, not one cross-component runtime dependency. No shared-source import or permanent hash equality requirement is added.

## Root cause
The current PiServer CSS contains fallback `:root` values and dynamic `theme.js` runtime variables plus persisted custom overrides. Future patches could inadvertently copy fallback hex values into new panels, swap fault/pending/applied status colors, lose the historical localStorage key, or introduce inconsistent icon/touch-target spacing. This R45 work formalizes accepted policy without changing appearance or user-owned settings.

## Files changed and exact behavior
1. `PiServer/UI_DESIGN_TOKENS.md` (new): scope the existing `opsFlat` runtime tokens (background/panel, amber accent, greenish `--ok`, `--warn`, `--danger`, muted text), compact layout variables `--font-scale=80%`, `--gap=4px`, `--workspace-pad=10px`, `--panel-pad=12px`, `--card-gap=10px`, `--field-gap=10px`; new-icon guidance **16px inline / 18px toolbar / 44px touch target** without changing existing controls; labels must distinguish Save, Apply and STOP and report backend-confirmed states. Emphasize that CSS fallback defaults differ from dynamic runtime theme.
2. `PiServer/tests/test_ui_style_tokens_r45.cjs` (new): **12 Node tests** executing the real component-local `theme.js` in VM mock browser/localStorage, semantic variables, compact sizing and status colors, override application, persistence across reapply and reload, deliberate reset, invalid saved data, stable public API/key, CSS status selectors, focus and mobile tap targets. Test does not launch browser/motor or mutate real user storage.
3. `PiServer/README.md`: short link to the R45 guide and smoke command; existing sections untouched.
4. `PiServer/piserver/app.py`: only `APP_VERSION = "0_4_23"` → `0_4_24` to mark/cache-bust the forward patch. All backend status, motor control, watchdog, settings/Apply and Pi model behavior unchanged.
5. `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_24.md`: this note.

**Not changed:** `piserver/web/static/theme.js`, `styles.css`, `settings.js`, `preview_freshness.js`, runtime configs, motor/camera/model services, API mutation semantics or user localStorage. No reset calls inserted and no extra theme classes.

## Verification actually performed
- Inspected and **executed the live current theme.js** in an isolated V8 mock document/localStorage for PiServer and CustomDrive GUI. **18/18 combined live-theme assertions passed** (9 per component), including original semantics, derived font scale, custom override retention across apply/reload, explicit reset and safe corrupt storage behavior. This was a runtime theme-function execution **without a real browser**, not a visual screenshot.
- Committed the 12-case Node test file, but **the standalone `node --test` suite has not been run** from a checkout of the exact GitHub branch. No real Pi/Chrome screenshots, UI screenshots, hardware or Python suite performed.
- Final direct-parent GitHub compare and anti-rollback inspection must be performed before opening the draft.

## Known limits and release gate
- New-icon size guidance is normative for *future* icons only; no existing SVG/CSS/icon dimensions are changed. Tests guard semantic identities and persistence, not pixel-level screenshot stability.
- Existing `PiServerStyleCustom:v0_3_5` user style key is historical and must not be renamed; `resetCustomOverrides()` remains explicit operator action, not a patch default.
- Run `node --test PiServer/tests/test_ui_style_tokens_r45.cjs`, then prior R30/R31/R35/R36/R43 suites and full PiServer tests. Compare operator screen at 390/768/1024/desktop; custom style override survives reload, Save/Apply works, STOP and keyboard focus obvious, preview remains fresh and 60ms control loop unaffected.
- Draft only; do not merge ahead of R43/R36/R35 without user approval.
