# piTrainer 0.11.8 — R45 UI design-token contract and drift tests

## Request
Complete the piTrainer portion of roadmap **R45 — UI design tokens and drift control**, using the actual current `DOCS/FORMAT_AND_STYLE_GUIDE.md`, `piTrainer/ui/formatting.py`, `ui/styles.py`, and `ui/theme.py`. Document central spacing/density, semantic status/action roles, concise labels and new-icon sizing guidance. Add small low-cost regression checks that alert on accidental theme/spacing drift, without reverting current Windows UI, saved splitters, R37–R40 logic, or user theme/density preferences.

## Exact parent and prior notes
- Parent branch: `update/pitrainer-0_11_7-r40-run-comparison`, **draft PR #56**, actual head SHA `8470995f49ab3e429efcd463eaa543cde74049f9`. R45 branch `update/pitrainer-0_11_8-r45-style-contract` is a stack on that head; no merge/rollback.
- Read latest component notes `PATCH_NOTES_piTrainer_0_11_7.md` (R40 run provenance/comparison), plus previous **0_11_6** (R39 background tasks), **0_11_5** (R38 preview cache) and **0_11_4** (R37 Data selection scope). All their runtime source remains unmodified.
- Inspected real launcher `piTrainer/main.py`, current version file, central style guide, `ui/formatting.py`, `ui/styles.py`, `ui/theme.py`, and existing tests. Honor 0_11_x patch numbering; this documentation/test-only update advances the existing displayed version `0.11.7 → 0.11.8` without editing gate settings.

## Root cause
The existing V11 guide describes roles and profile ownership, but future page patches still risk adding local hardcoded hex values, independently chosen spacing or icon sizes, inconsistent warning versus main actions, and stylesheet placeholders that aren't backed by central tokens. No measurable rendering bug was claimed, and a redesign was not requested.

## Files changed and exact behavior
1. `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md` — insert a **R45 token contract** beside existing Colour roles: compact/comfortable/spacious thresholds, documented actual comfortable spacing (page 7, panel 6, form 9/6 pixels), green primary/nextStep, amber prerequisite, danger/error and subdued hints, short labels and recommended new-icon sizes (16/18/20 px across profiles) with text labels. This is **new-panel guidance only**, not a forced resize of existing icons. Explicitly preserve saved splitters/density, R40 history and model artifacts, status feedback and existing default UI styling.
2. `piTrainer/tests/test_ui_style_contract_r45.py` — **15 stdlib-only AST tests**: source parse and density monotonicity, central role/colour names, full CSS placeholder coverage, existing style-button selectors, responsive width rules, widget-role fallback, guided label/icon policy, splitter preset names and forward version marker. The test avoids PySide6/TensorFlow imports and has no database or file writes.
3. `piTrainer/piTrainer/version.py` — advance only `APP_VERSION=0.11.8` and `PATCH_VERSION=piTrainer_0_11_8` using the accepted scheme. Main window title is derived from these existing strings; no version-gate configuration changes.
4. `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_8.md` — this note.

**No runtime changes** to `ui/formatting.py`, `ui/styles.py`, `ui/theme.py`, page/panel CSS, workers, model processing, preview caches, current UI state, version gate, system config or saved user data. No shared cross-component stylesheet.

## Verification actually performed
- Inspected current GitHub source and latest 4 component notes, not the old baseline ZIP. Verified central stylesheet calls `stylesheet_tokens(density)` and roles map to `THEME_COLORS`.
- Tested central source/role/placeholder invariants by live-source static inspection in the connected GitHub workspace; these are **not** Qt screenshot or code-execution tests.
- The new **15 Python tests were committed but not run as a standalone Python test suite** against a local checkout; PySide6/TensorFlow GUI, real Windows screenshots and full piTrainer suite are not tested here.
- Run final GitHub branch compare against R40 parent before draft PR; preserve no-file-deletion, no unrelated-component and no style/runtime-file-touch guarantees.

## Release gate and limitations
1. From `piTrainer/`, run `python -m unittest discover -s tests -p 'test_ui_style_contract_r45.py' -v`, then the full test suite.
2. On Windows/PySide6, inspect compact, comfortable and spacious widths; primary green/amber prerequisite/danger roles; Data/Preprocess/Train/Validate/Export tabs, banner, display, scrollbars and splitter restoration. Confirm new version is allowed by your actual access-control policy before distributing.
3. A future intentional palette or density change may update this contract and the corresponding smoke tests after explicit review. Do not use the test as authorization to overwrite a user's preferred theme or persisted panel sizes.
4. **No PR merges authorized.** R45 must remain stacked above R40 and its R39/R38/R37 dependencies.
