# PiServer 0.4.40 — Batch 8/9 modular browser layout and operator workspace

Reviewed live server.py, current dashboard JS/HTML/CSS and previous four notes 0.4.39/38/37/36. Last green 581c049, Linux CI 45531850972 and Windows CI 45531851593. Later trainer/PiSD candidate changes retained.

- Extract pure layout cloning/merge and preset definitions into component-local layout_presets.js; existing storage key and saved/default merge semantics retained. No server route changes.
- Add page-specific Driving, Camera tuning and Model testing layout previews. Preview changes only boxes in the existing workspace; no page switch, motor command, theme write or layout persistence. Cancel restores exact prior visible boxes, page switch cancels, explicit Save commits. Existing drag autosave remains outside preview; drag/reset disabled during preview.
- Optional essentials-only status tier keeps error, drive, applied output, preview, and overlay control visible; full existing metrics remain default. Browser-local toolbar feedback distinguishes layout from runtime changes.
- Pure geometry/merge tests and actual Chromium preview/cancel/save/status-tier assertions registered. Version marker only for Python.

New CI pending. Owner screenshots, physical hardware and full workspace acceptance remain separate. No proposal closure.

## Native browser correction
CI 45538852480 failed the PiServer native browser step at all four viewport widths: real checkbox clicks intercepted by the metric grid/header. The existing status grid allocated its first row minmax(0,1fr); the new density control occupied that row, collapsing/overlapping it. Make the actual Status dock body one scrollable flex column with nonshrinking children and intrinsic metric rows. Keep previous card geometry fix, all metrics, layout presets, safety controls and existing persistence. Preserve actual pointer interaction assertion and add native keyboard toggle check. Linux PiSD, trainer and compatibility jobs and hosted Windows 45538852452 passed. Corrected exact-candidate CI required. Same unreleased version.
