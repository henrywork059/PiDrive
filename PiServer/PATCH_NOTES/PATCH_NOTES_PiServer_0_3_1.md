# PiServer 0_3_1 Patch Notes

## Summary
Added a new **Style settings** button beside **Save layout** in the top toolbar. It opens a web-style settings dialog where the user can preview and adjust key UI appearance values such as colors, spacing, radius, and font scale.

## Requested change
- Add a settings button next to **Save layout**
- Let the user change web style values such as:
  - colors
  - margin / spacing
  - font size
  - panel / box appearance
- Include an example preview panel and boxes inside the settings UI

## Root cause / gap
PiServer already had a theme layer and CSS variables, but there was no user-facing editor for them. The style system was only defined in code, so changing the look required manual editing of front-end files.

## What changed

### 1) Toolbar button added
File:
- `piserver/web/templates/index.html`

Changes:
- Added a new **Style settings** button next to **Save layout**
- Added a modal dialog for editing UI appearance

### 2) Style settings modal added
File:
- `piserver/web/templates/index.html`

Changes:
- Added a modal with:
  - color pickers for background, panel, panel alt, text, muted, accent, danger, warn, and ok colors
  - sliders for font size, outer margin, panel gap, panel radius, button radius, box radius, panel padding, and header spacing
- Added a live preview area containing:
  - an example panel
  - example boxes / cards
  - preview status banner

### 3) Theme persistence extended
File:
- `piserver/web/static/theme.js`

Changes:
- Added custom style override storage in browser `localStorage`
- Added helper methods for:
  - reading current resolved style variables
  - saving custom overrides
  - resetting overrides back to theme defaults
- Kept the existing theme system intact while allowing user-level overrides on top

### 4) Front-end behavior added
File:
- `piserver/web/static/app.js`

Changes:
- Added style settings field definitions
- Added modal open / close handling
- Added live preview updates while sliders and color pickers move
- Added save / reset behavior
- Updates persist per browser through local storage
- Accent color updates also refresh the RGB helper variable used elsewhere in the UI

### 5) CSS variable support expanded
File:
- `piserver/web/static/styles.css`

Changes:
- Added reusable variables for:
  - font scale
  - workspace padding
  - panel padding
  - panel header padding
  - control radius
  - card radius
- Connected existing UI elements to those variables
- Added modal styling and responsive layout for the settings dialog

## Behavior notes
- Style settings are currently **browser-local**, similar to layout persistence
- This means different devices / browsers can keep different visual preferences
- Closing the dialog without saving reverts the temporary preview to the last saved style state
- Reset returns the style to the default PiServer theme values

## Verification performed
- Verified JavaScript syntax with:
  - `node --check piserver/web/static/app.js`
  - `node --check piserver/web/static/theme.js`
- Verified the required files were updated and patch notes added

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_1.md`

## Known limitation
- This patch does not yet sync style settings to the PiServer backend or across users; persistence is local to the browser.

## Possible next improvements
- Add preset themes (compact / classic / high-contrast / classroom)
- Allow export / import of style presets
- Add separate controls for borders, shadows, and topbar colors
- Add per-page style presets if you want different looks for Manual / Training / Camera tabs
