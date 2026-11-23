# CustomDrive UI token contract (R45)

CustomDrive contains **two distinct live web surfaces**, and this document
records their existing visual rules. It does not merge theme engines, change
user settings, or propagate PiServer CSS into either app.

## 1. General GUI — `custom_drive/gui_web/`

Source of truth: component-local `static/theme.js` for operator theme and
saved overrides, `static/styles.css` for widget, layout and responsive
rules. This GUI's `theme.js` is **currently byte-identical** to PiServer's
but both files are **separately owned**. Future intentional differences are
valid; do not add a mandatory cross-repository byte-hash check or a runtime
cross-component dependency.

| Design concern | Accepted runtime tokens / selectors | Future-panel policy |
| --- | --- | --- |
| Dark surfaces | `--bg #1b1d23`, `--panel #232630`, `--panel-alt #2a2e39` | Consume `var(--bg)` / `var(--panel)`. |
| Operator accent | `--accent #f4a31e`, `--accent-rgb 244,163,30` | Active/selected UI only; do not equate it with confirmed motor readiness. |
| Status | `--ok #8d9d61`, `--warn #f4a31e`, `--danger #ca655d`, `--muted #9ea5b5` | Continue `.banner.good/.warn/.muted`, `.badge.estop`, `.preview-health.paused/.disconnected`, and applied/failed settings badges. Text must name the actual state. |
| Compact density | `--font-scale 80%`, `--gap 4px`, `--workspace-pad 10px`, `--panel-pad 12px` | Stay within current compact control-panel geometry; no unilateral panel resizing. |
| Shapes/spacing | `--card-gap 10px`, `--field-gap 10px`, `--control-radius 12px`, `--card-radius 14px` | Use theme variables rather than per-panel hardcoded equivalents. |
| Labels and actions | `Start`, `Stop`, `Apply`, `Save`, `Rearm` | Keep concise action/object text and indicate when hardware motion is possible. Avoid naming a pending action `Applied` until backend confirms. |
| Icon sizes | No enforced icon-size runtime token exists | **Guideline for new icons only:** 16px inline status glyph, up to 18px toolbar glyph, nearby text label, and at least 44px mobile interactive target. Do not retrofit existing icon sizes in R45. |

`window.PiServerStyle` and the historical
`PiServerStyleCustom:v0_3_5` storage key also exist within CustomDrive's
GUI. **Keep both unchanged.** Reapplying the theme must retain existing
user overrides and derived font scale. The override's key name is
historical; rename/migration would risk losing users' saved styles.
The current `:root` fallback CSS and dynamic JS theme are different
layers; the resolved runtime theme is authoritative in the browser.

## 2. Mission 1 — `custom_drive/mission1_web/`

Mission 1 has its **own** standalone `static/styles.css`, distinct
from the general GUI palette. Do not force it to load `gui_web/theme.js`.

| Design concern | Existing implementation | Contract |
| --- | --- | --- |
| Surfaces/links | `--bg #0b1220`, `--panel #101827`, `--text #e5edf9`, `--muted #9fb0cc`, `--accent #38bdf8` | Keep the separate blue/cyan Mission UI; no unreviewed conversion to the GUI's amber theme. |
| Progress | `.mission-progress-step[data-step-state]` uses **blue current**, **green completed**, **red failed**, **amber interrupted** | These colors show states actually observed in R33's server-backed timeline; keep textual stage/outcome/last transition. Never infer that an unobserved stage is completed. |
| Grip/drop-off | R44 `.overlay-trigger-pickup` green and `.overlay-trigger-dropoff` amber; `100% top`, `50% middle`, `0% bottom` | Keep separate values and the explicit unsaved-preview readout; do not reverse U24's coordinate mapping or change the servo gate. |
| Spacing | Main panel `padding 16px`, dashboard `gap 16px`, 16:9 live-frame stage | Keep R36 phone breakpoints, scrollable tables and comfortable touch controls. |
| Labels and feedback | `Grip`, `Drop-off`, `Preview only`, `Saved on server`; stage names in timeline | Name the action and distinguish operator draft from backend effective setting. A failed save does not enable arm motion. |
| Icon sizes | Current overlay ticks are geometric SVG features, not UI button icons | Future inline icon guideline **16px**, toolbar/action glyph **18px**; keep icon + readable text and **44px minimum** mobile target. Do not alter existing overlay ruler labels. |

## Drift and release checks

Run from monorepo root:

```bash
node --test CustomDrive/tests/test_ui_style_tokens_r45.cjs
```

The Node smoke checks execute the **real component-owned general GUI theme**
inside a fake document/localStorage, assert saved user style overrides
survive reapply and reload, and inspect the *existing* CSS status/spacing/
focus/phone selectors in both GUIs. This test enforces **semantic ownership**
but does not assert permanent byte equality with PiServer.

Before promoting, run all existing R33/R35/R36/R43/R44 regression suites,
then inspect live GUI and Mission 1 at 390px, 768px, 1024px and desktop,
including E-stop, arm keyboard release, status icons, Preview only/Saved
on server, trigger labels and Mission 1 timeline. No motor, servo, camera,
settings persistence or launcher behavior is changed by token-policy text.
