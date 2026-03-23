# PATCH NOTES — PiServer_0_4_2

## Baseline
- Stable baseline used: `PiServer_0_4_0`
- Patch line: `0_4_x`
- This is a patch-only package.

## Problem reported
The current PiServer **Style settings** popup on the main page was still showing the older layout:
- the **Spacing and shape** area did not properly scroll to reveal all controls
- the lower controls could overlap or appear broken
- the preview area only showed a minimal example
- the narrow status layout still struggled to keep all boxes visible

## Root cause
1. The active PiServer UI in the repo still used the **older modal embedded in `index.html`**, not the newer standalone settings template.
2. The modal markup had a broken nesting point in the **Spacing and shape** section, which could cause the card/field spacing rows to render incorrectly.
3. The modal body was scrollable as one large block, but the **Spacing and shape** section itself was not independently scrollable.
4. The preview section was too limited to properly test spacing, box radius, fields, and narrow-panel behavior.
5. The status metric grid still used a relatively wide minimum size, which made tight layouts less flexible.

## Changes made
### 1) Refreshed the active main-page settings popup
Updated `piserver/web/templates/index.html` so the **Style settings** button on the PiServer page opens an improved popup with:
- cleaned/fixed control markup
- a dedicated **Colors** section
- a dedicated **Spacing and shape** section
- a larger **Preview** section with multiple examples

### 2) Made **Spacing and shape** independently scrollable
Updated the popup structure and CSS so the spacing/shape controls now sit inside their own scrollable area.
This allows all controls to remain accessible without the whole popup becoming awkward to use.

### 3) Added more preview examples
Expanded the preview area to include:
- a status-style panel
- a controls/fields panel
- a narrow status panel example
- an extra message/cards example

This makes it easier to see the effect of font size, card spacing, field spacing, panel padding, and radius changes.

### 4) Improved narrow status behavior
Added late CSS overrides so the live PiServer status metric grid can pack more tightly when a panel becomes narrow.
Also added safer wrapping for card values.

### 5) Bumped static app version
Updated `APP_VERSION` in `piserver/app.py` to `0_4_2` so browser cache busting works after file replacement.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_2.md`

## Verification performed
- Python syntax check run on `piserver/app.py`
- Reviewed the final modal HTML structure after replacement
- Confirmed the cache-busting app version is now `0_4_2`

## Apply steps
1. Replace the files in your PiServer repo with the files from this patch.
2. Restart PiServer:
   ```bash
   python server.py
   ```
3. Hard refresh the browser once:
   ```text
   Ctrl + Shift + R
   ```
4. Open **Style settings** from the main PiServer page.

## Expected result
- The **Style settings** popup on the main PiServer page should look updated
- **Spacing and shape** should scroll properly
- the preview area should show several example blocks
- narrow status cards should fit more reliably

## Notes
- This patch updates the **active popup used by the main PiServer page**.
- The separate `settings.html` file in the repo was not the currently active UI path for the screenshot you provided, so this patch targeted the real in-use page first.
