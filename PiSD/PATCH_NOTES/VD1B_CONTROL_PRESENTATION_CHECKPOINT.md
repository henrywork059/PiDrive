# Visual Design Update 1B — control-state presentation

`pisd/web/static/css/pisd_design_system.css`: opt-in dark/light disabled action styling, replaces faded active colors with readable muted/surface colors and suppresses decorative hover feedback. Forced colors unchanged. `tools/check_vd1a_web.py` checks actual visible AI download button in a temporary disabled presentation state; no handler called.

Base: exact PR #104 stability checkpoint `bbc07dda3a162ce6fc17f646dcfe8688b7bf1c56` (four applicable CI workflows successful; camera workflow skipped). Work is stacked; no merge or promotion.

Scope: VD14 partial, enabled/disabled action presentation only. Preserve existing role meanings, native focus/geometry, actual disabled state, runtime handlers, STOP, data/config, saved layouts and historical notes. No component version change during provisional 1.0.0 development. Existing approved baseline remains pinned.

Verification: source anchors checked; stylesheet brace balance and nine palette contrast pairs calculated (all >=4.5:1). Added candidate tests to existing registered browser/Qt suites. Actual candidate CI, artifact inspection, owner review and physical tests pending. Local environment lacks Qt and Git network checkout; no local rendered UI claimed.
