# PATCH NOTES — PiServer_0_4_1

## Baseline
- Stable baseline before this patch: **PiServer_0_4_0**
- Patch type: **UI / web settings / layout robustness**

## Requested changes
1. Make **Spacing and shape** scroll so all settings can be viewed.
2. Add **more preview examples** on the style settings page.
3. Fix the **status panel** so narrow panels can still show all boxes instead of hiding or dropping them.

## Root causes found
### 1) Settings page wiring was incomplete
The repo already contained a `settings.html` and `settings.js`, but they were not fully wired into the running app:
- there was **no `/settings` route** in `piserver/app.py`
- the main PiServer page button still pointed at the old in-page modal behavior in `app.js`
- `settings.js` was calling theme API methods that did **not exist** in `theme.js`

This meant the separate settings page was only partially present in the repo and not reliable as the real settings workflow.

### 2) Settings page layout styles were missing
The settings page template had many custom classes, but the stylesheet did not define a full settings-page layout. Because of that, scrolling and layout behavior were inconsistent and fragile.

### 3) Narrow status panel behavior was still constrained by old compact rules
Earlier compact/theme rules still made the status panel more aggressive than desired at narrow widths. The result was that some cards could become effectively hidden or not remain comfortably visible when the status panel became very narrow.

## Final changes made
### A. Turned the settings flow into a real routed page
- Added **`/settings`** route in `piserver/app.py`
- Updated the main **Style settings** button behavior in `piserver/web/static/app.js` so it opens the dedicated settings page
- Removed the old broken trailing modal block from `piserver/web/templates/index.html`

### B. Rebuilt the style settings state API in `theme.js`
- Replaced the old partial override storage logic with a cleaner settings-based API
- Added stable storage key for this patch line
- Added migration support from older local-storage style keys when possible
- Exposed settings functions used by the settings page:
  - `getDefaultSettings()`
  - `loadCustomSettings()`
  - `saveCustomSettings()`
  - `clearCustomSettings()`
  - `applyCustomSettings()`
  - `applySavedSettings()`
- Kept compatibility helpers such as `getResolvedVars()` / `saveCustomOverrides()` so the rest of the frontend remains safe

### C. Reworked the settings page itself
- Rewrote `piserver/web/templates/settings.html`
- Added a dedicated **Spacing and shape** card
- Made the settings cards internally scrollable so all content can be reached
- Added more preview content:
  - topbar preview
  - wide status preview
  - narrow status preview
  - controls panel preview
  - record/cards preview

### D. Added missing settings-page CSS
In `piserver/web/static/styles.css`:
- added settings page layout/grid/card styling
- added scroll behavior for settings cards
- added responsive layout rules for smaller screens
- added styling for preview sections and link-style buttons

### E. Fixed narrow status panel behavior on the main PiServer page
At the end of `styles.css`, added stronger final overrides so the status panel behaves better when narrow:
- panel body can scroll instead of clipping content
- status metric grid uses tighter responsive card sizing
- low/medium priority cards are explicitly kept visible inside the **status** panel at narrow widths
- at very narrow widths, the status cards fall back to a single-column stack instead of disappearing

### F. Version bump for cache busting
- Updated `APP_VERSION` to **`0_4_1`** so the browser requests the new static files instead of stale cached ones

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/static/settings.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/templates/settings.html`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_1.md`

## Verification performed
### Static verification
- Python syntax check:
  - `python -m py_compile ...` on the updated PiServer Python files
- JavaScript syntax check:
  - `node --check piserver/web/static/theme.js`
  - `node --check piserver/web/static/settings.js`
  - `node --check piserver/web/static/app.js`

### Manual logic verification
Confirmed the updated flow is now internally consistent:
- main page button opens `/settings`
- `/settings` exists in Flask app
- settings page JS now calls real theme API methods
- saved settings remain applicable to the main PiServer page through the shared theme loader
- status panel CSS now favors visibility/stacking/scrolling over hiding cards

## Notes
- Style settings remain **browser-local** (localStorage), not server-global.
- After applying this patch, restart PiServer and do one hard refresh (`Ctrl + Shift + R`) so the new `0_4_1` static assets are definitely loaded.
