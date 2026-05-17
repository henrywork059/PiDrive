# PiSD Colour Palette

PiSD now uses one shared semantic colour palette. New pages and panels should use these tokens instead of inventing new colours.

The source of truth is:

```text
PiSD/pisd/core/presentation_registry.py
PiSD/pisd/web/static/css/pisd_design_system.css
```

## Semantic colours

| Token | Hex | Use |
|---|---:|---|
| `page_bg` | `#07101d` | Page background |
| `surface` | `#0f172a` | Main panel/card surface |
| `surface_soft` | `#1e293b` | Buttons, secondary panel areas |
| `line` | `#334155` | Borders and separators |
| `text` | `#e5eefc` | Main readable text |
| `muted` | `#98adc9` | Labels and quiet helper text |
| `primary` | `#38bdf8` | Primary actions and section labels |
| `ok` | `#22c55e` | OK/status indicators |
| `warning` | `#f59e0b` | Caution/armed controls |
| `danger` | `#e11d48` | STOP/error/destructive actions |
| `recording` | `#ef4444` | Active recording indicator |
| `capture` | `#14b8a6` | Successful capture notices |

## Development rules

- Use semantic colour variables first, such as `--pisd-palette-primary`, `--pisd-palette-danger`, and `--pisd-palette-recording`.
- Do not hard-code new page-specific colour schemes.
- Keep status colours consistent with error codes: green for `PISD-OK-*`, red/pink for errors, amber for caution/armed motor output.
- Recording state must be visibly different from normal status.
- Single-frame capture confirmation should use the capture/accent colour, not the error colour.
