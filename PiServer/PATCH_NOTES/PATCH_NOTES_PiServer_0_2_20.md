# PiServer 0_2_20 Patch Notes

## Baseline used
This patch was built directly from the user-provided `piserver.zip` baseline in the current chat to avoid rolling back newer PiServer work.

## Goals
- Keep more status cards visible when the status panel becomes narrow.
- Improve the default workspace layout.
- Reduce extra space, padding, and margins across the UI.
- Avoid old browser-saved layouts masking the new defaults.

## Files changed
- `piserver/app.py`
- `piserver/web/static/app.js`
- `piserver/web/static/styles.css`

## What changed

### 1) Status panel visibility improved
- Reduced status metric card padding, label size, and value size.
- Reduced grid minimum widths so more cards fit per row.
- Added scrolling to the status panel body so cards are still reachable if the panel is manually resized smaller than intended.

### 2) Better default layouts
- Increased the default status panel size from 4 rows to 5 rows.
- Gave the status panel more horizontal space in all default pages.
- Rebalanced the viewer / side-panel arrangement for manual, training, auto, camera, and motor pages.

### 3) Tighter spacing
- Reduced workspace gap, workspace padding, top bar padding, panel header padding, panel body padding, field gaps, form spacing, note spacing, and banner spacing.
- Tightened button sizing and general control density.
- Reduced some viewer overlay spacing.

### 4) Prevent old saved layout from hiding the new defaults
- Bumped the layout localStorage key prefix to `PiServerLayout:v0_2_20:` so the browser loads the new default arrangement automatically.

## Version bump
- `APP_VERSION` updated from `0_2_19` to `0_2_20`.

## Verification
- Python syntax check: `python -m compileall piserver`
- JavaScript syntax check: `node --check piserver/web/static/app.js`

## Apply instructions
Copy these patched files into your current `PiServer` project root, preserving paths. Then restart the server and hard-refresh the browser once.
