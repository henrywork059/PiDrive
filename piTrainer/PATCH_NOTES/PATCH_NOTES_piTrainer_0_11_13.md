# piTrainer 0.11.13 — Batch 4 / R35 session controls keyboard accessibility

Direct parent 53b06b7 (CI 45380631288 4/4). Reviewed current session panel, main window, styles, selection tests and notes 0.11.12–9. Root input and per-session checkbox lacked explicit accessible names; session-list height handle was mouse-only. Add names, keyboard Up/Down resize (20px) and Home reset using existing clamped persistence callbacks, visible focus styling using existing INFO token. Native Qt tests use a disposable INI and synthetic sessions. Existing mouse behavior, selection, saved height bounds, layout and training/export code retained. Exact candidate CI pending; no native Windows/physical acceptance.

## Verification and R50 coverage
CI 45384279829 passed all four jobs, including the three native session-control tests and prior selection regressions. Add an independent native DockPage splitter save/restore/resize test using a temporary QSettings INI, with zero soft minimums to isolate proportional persistence. No trainer runtime source or version change in this follow-up; real workspace minimum-size behavior and Windows acceptance remain separate. Exact new candidate CI required.
