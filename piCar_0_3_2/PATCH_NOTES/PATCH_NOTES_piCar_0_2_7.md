# PiCar Patch Notes — piCar_0_2_7

## Summary
This patch makes **each right-side panel independently scrollable** (Mode / Manual / Record / Status / Viewer) when the device screen is too small to display all content at once.

You can now scroll **inside a panel** to read/operate all controls without the whole page getting stuck.

## Problem / Cause
- The UI uses a fixed grid layout sized to the viewport (`100vw x 100vh`) with `body { overflow: hidden; }`.
- Panels were `display: flex; flex-direction: column;` but **had no internal scroll container**, so when content exceeded panel height (common on phones / small tablets), the extra content became inaccessible.

## What I Changed
### 1) Added a scrollable panel content container
- Added a new `.panel-body` container inside each panel.
- CSS:
  - `.panel-body { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; }`
  - `min-height: 0` is critical in flex layouts so the child can actually shrink and scroll.

### 2) Kept the Live Viewer centered while allowing scrolling
- Moved “center content” behavior from `.panel-viewer` to `.panel-viewer .panel-body`.
  - This preserves the centered video layout without breaking panel-title + scroll.

### 3) Updated all panel templates to use the new structure
- `ui_status_panel.py`
- `ui_viewer_panel.py`
- `ui_model_panel.py`
- `ui_manual_panel.py`
- `ui_record_panel.py`

## Files Changed
- `ui_base.py`
- `ui_status_panel.py`
- `ui_viewer_panel.py`
- `ui_model_panel.py`
- `ui_manual_panel.py`
- `ui_record_panel.py`

## Verification Steps (Pi)
1. Start server:
   - `cd ~/piCar && python3 server.py`
2. Open UI on:
   - Phone (small screen)
   - Tablet
   - PC
3. Confirm:
   - When a panel is too short, you can **scroll inside that panel**.
   - Other panels stay in place (no overlay).
   - Live Viewer remains centered and visible.

## Notes / Future Improvements
- Optional: add subtle custom scrollbars (WebKit) for better visibility.
- Optional: add “sticky” panel titles (so the title remains visible while scrolling).
