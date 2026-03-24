# PATCH NOTES — PiServer_0_4_4

## Summary
This patch is a focused follow-up on top of the current 0_4_x styling work. It does **not** roll back the in-page Style settings popup or the recent preview/status updates.

It fixes two reported problems:
1. rounding and colour settings were still only partially visible because older hard-coded theme rules kept winning over the saved style variables
2. the Status panel still hid too many boxes in narrow layouts because older priority hide rules were still active and the metric grid was not packing densely enough

## Root causes
- Several late CSS rules from the legacy compact theme still applied hard-coded backgrounds, borders, and radius values with strong specificity. The saved style settings were updating CSS variables correctly, but those values were not consistently driving the actual UI surfaces.
- The narrow Status panel still inherited global `priority-low` / `priority-medium` hide rules at small widths. That meant cards disappeared even when vertical space remained available.
- The Status panel also needed denser padding and tighter grid sizing at narrow widths so more cards could remain visible before scrolling.

## Final changes
### 1) Hardened style-variable application
Added a new late CSS override block so the saved style settings visibly affect the real PiServer page instead of only some surfaces.

This now forces the current style variables onto:
- page background
- top bar
- dock panels
- modal card
- settings sections
- preview surface
- cards / banners / panel sections
- buttons / selects / numeric inputs / colour inputs
- muted text labels
- panel, card, and control rounding

### 2) Dense narrow Status layout
Reworked the Status panel layout so it uses available height better and keeps more cards visible.

Changes:
- status body now uses a grid layout with a scrollable metric area and a separate banner row
- status metric grid now packs more densely with smaller min card widths
- narrow Status panels no longer hide `priority-low` and `priority-medium` cards
- status cards compact further at narrow widths by reducing padding and text size
- overlay status button is forced to remain visible as a flex card
- very narrow panels fall back to 2-column and then 1-column layouts instead of hiding cards

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_4.md`

## Versioning
- App/static version bumped from `0_4_3` to `0_4_4`

## Verification
1. Replace the patched files.
2. Restart PiServer with `python server.py`.
3. Hard refresh once with `Ctrl + Shift + R`.
4. Open **Style settings** and change:
   - panel radius
   - button radius
   - box radius
   - background / panel / panel alt / accent colours
5. Confirm the main PiServer page visibly updates those surfaces.
6. Narrow the **Status** panel and confirm:
   - more cards stay visible
   - cards compact instead of disappearing early
   - remaining overflow is scrollable inside the status metric area

## Notes
- This patch is additive and keeps the current in-page Style settings popup and preview flow intact.
- It is designed specifically to avoid rolling back the recent 0_4_1 to 0_4_3 behaviour.
