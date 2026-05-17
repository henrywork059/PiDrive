# PiSD Responsive Layout System

Version: 0.3.7

## Purpose

PiSD now uses a shared responsive layout layer so every page follows the same panel placement rules. This prevents page-specific CSS or saved presentation settings from moving important panels into confusing positions.

The final layout authority is:

```text
pisd/web/static/css/pisd_layout_system.css
```

The saved presentation defaults and development rules are defined in:

```text
pisd/core/presentation_registry.py
```

Runtime/user presentation settings are stored through:

```text
config/runtime_settings.json
```

## CSS loading order

Every GUI page must load CSS in this order:

```text
panel_presentation_global.css
page-specific css
unified_layout.css
pisd_design_system.css
pisd_layout_system.css
```

`pisd_layout_system.css` must be last. It is allowed to override page CSS when the page CSS would break the shared responsive layout.

## Page layout roles

All panels should use one of these roles:

```text
status
preview
drive
control
settings
log
```

Role weights from the settings page may affect size/proportion only. They must not change the semantic order of safety-critical panels.

## Manual Drive layout contract

Wide / PC / iPad landscape:

```text
status  status
preview drive
preview stop
log     log
```

Small / phone / portrait:

```text
status
preview
drive
stop
log
```

Rules:

- Status must appear before Camera Preview in the DOM and in the layout.
- Camera Preview must sit directly below the Status strip on PC/iPad layouts.
- Manual Control / drag pad must sit in the control column on PC/iPad layouts.
- STOP must always be visible and must not be inside the collapsible log.
- The action log should stay hidden until opened.

## Breakpoints

The layout system uses three practical ranges:

```text
wide:   1100px and above
medium: 760px to 1099px
small:  below 760px
```

For height-constrained screens, the preview height uses `svh` and clamp rules so the camera panel remains usable without forcing excessive scrolling.

## Development rules

When adding a new page:

1. Use existing panel classes and `data-panel-role` attributes.
2. Load `pisd_layout_system.css` last.
3. Do not create page-specific grid rules that override semantic order.
4. Put reusable colours, spacing, and panel tuning in `presentation_registry.py` and the shared CSS files.
5. Add a static validation script or extend `scripts/test_responsive_layout_contract.py`.

## Validation

Run:

```bash
python3 scripts/test_responsive_layout_contract.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
```

The important expected result is:

```text
OK   PISD-OK-000   responsive_layout.source_contract - shared responsive layout contract passed
```
