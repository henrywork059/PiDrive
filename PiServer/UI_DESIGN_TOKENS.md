# PiServer UI token contract (R45, 0_4_24)

This is the **review policy for future UI panels**, not a new theme engine.
The source of truth remains the component-local files
`piserver/web/static/theme.js` and `piserver/web/static/styles.css`.
No user theme, saved panel layout, settings Apply path, preview/control
tick, or safety behavior is reset by this patch.

## Established design tokens

The live `theme.js` installs the `opsFlat` theme and CSS custom properties on
`document.documentElement.style`. The early `:root` values in
`styles.css` provide fallback styling but **are not the final browser
palette** when JS applies theme overrides. Keep those layers distinct.

| Role | Current runtime token/value | New-panel rule |
| --- | --- | --- |
| App/panel | `--bg #1b1d23`, `--panel #232630`, `--panel-alt #2a2e39` | Use `var(--bg)` and `var(--panel)` rather than copied hex. |
| Primary UI emphasis | `--accent #f4a31e`, `--accent-rgb 244, 163, 30` | Use for selected/active UI, not for safety OK or destructive errors. |
| Status | `--ok #8d9d61`, `--warn #f4a31e`, `--danger #ca655d` | Bind confirmed/success, pending/warning and fault/STOP to semantic names. Include a visible text label/code; do not use color alone. |
| Readability | `--text #f1f2f7`, `--muted #9ea5b5` | Use normal contrast for values; muted for supporting hints, never critical STOP. |
| Density | `--font-scale 80%`, `--font-scale-factor 0.8`, `--gap 4px` | Existing dense operator layout is intentional; adjust through existing theme settings, not page-specific overrides. |
| Spacing | `--workspace-pad 10px`, `--panel-pad 12px`, `--card-gap 10px`, `--field-gap 10px` | New panels use these properties for primary spacing; respect accepted responsive overrides. |
| Shape | `--control-radius 12px`, `--card-radius 14px`, `--radius 10px` | Reuse these, do not invent local rounded-card styles. |
| Text labels | Existing UI `Save`, `Apply`, `STOP`, `Start live` actions | Keep action + object short. Say if an action sends a command to the Pi. An applied badge means server-confirmed, not merely clicked. |
| Icon sizing | No globally required icon token currently exists | **Guideline only for new elements:** 16px inline status/action glyphs, up to 18px for toolbar icons, label alongside icon, and at least a 44px mobile interactive target. Do not resize current icons or controls in a contract-only patch. |

## Ownership and persistence

- `theme.js` currently uses `window.PiServerStyle` and the **existing
  storage key** `PiServerStyleCustom:v0_3_5`. Keep the key and
  `getResolvedVars()`, `saveCustomOverrides()`,
  `resetCustomOverrides()` entry points unchanged so user overrides
  survive restarts. **Never** overwrite local storage just to apply a new
  visual contract.
- `CustomDrive/custom_drive/gui_web/static/theme.js` is currently
  byte-identical but **owned by CustomDrive**. Document shared policy;
  do not import a cross-component JS/CSS file, enforce perpetual byte
  equality, or overwrite one theme from the other. Intentional divergence
  is permitted with explicit component review.
- Keep `styles.css` page rules, themes and mobile layouts intact. Do not
  delete pre-existing status/STOP selectors or change preview freshness.
  Avoid breaking a panel's saved width, scroll behavior, numerical input
  reachability or focus/keyboard accessibility.
- Always associate a text state and an operator-safe next step with any new
  warning; `--ok` must never imply a motor or settings mutation was
  accepted without backend confirmation.

## Drift smoke test / release gate

From the monorepo root:

```bash
node --test PiServer/tests/test_ui_style_tokens_r45.cjs
```

The stdlib Node test executes the **real** `theme.js` in a fake browser
with persistent `localStorage` and checks: named token availability,
semantic status colors, derived font scale, persistence through theme
reapplication and reload, deliberate reset behavior and presence of
accepted CSS status/focus/mobile semantics. It does **not** take screenshots
or drive motors.

For release, inspect 390px, 768px, 1024px and desktop operator pages,
Saved/Apply status, STOP, preview, sliders and modal focus. Test local style
overrides over page reload without wiping them. Run the component's
existing Node, Python and real Raspberry Pi UI tests before merging.
