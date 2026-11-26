# piTrainer 0.11.30 — Batch 4 / R35 Data workspace accessibility

## Request and verified baseline
Parent 0d1ef013f7cb2e882cb403b4227aa437e27e898c verified exact Linux 45753713021 (4/4) and Windows 45753713018 (1/1). PiSD 0.11.41 Revision C Chromium 32/32, Node 22/22 and standard validation 63/63. Reviewed actual main.py, root/component instructions, current active Data panels and existing mutation handlers, canonical R35, and piTrainer 0.11.29/28/27/26 notes.

## Cause and changes
- panels/data/frame_filter_panel.py: name text, mode, four numeric range bounds and Apply/Clear; add label buddies for text and mode.
- panels/data/bulk_edit_panel.py: distinct slider and normalized spinbox names/descriptions, explicit keyboard focus for both sliders, label buddies; no range or synchronization logic changes.
- panels/data/data_control_panel.py: named recovery count and label buddy.
- panels/data/model_deploy_panel.py: named model source, path, Browse, batch size and row limit.
- panels/data/merge_sessions_panel.py: named merged-session field and label buddy.
- panels/data/data_plot_panel.py: named selectors.
- panels/data/preview_panel.py: named read-only Records table with existing selection/keyboard scope description; no table selection/model changes.
- panels/data/session_source_panel.py: distinguish root Browse, Refresh, session list and selection actions; retain existing per-session checkbox names and resize behavior.
- ui/styles.py and ui/sliders.py: focus indicator for standard horizontal sliders and custom centered-fill steering sliders using existing theme tokens. No change to slider fill/scale or layout geometry.
- tests/test_validation_controls_r35.py: extend existing registered native Qt suite with distinct names, keyboard filter/recovery, slider synchronization and selection/confirmation gating. Callback fixtures do not write any dataset. Mock session path/height settings to avoid persistent writes in the new test.
- version.py, format/style guide and shared UI regression gate updated.

## Verification and limitations
Exact parent verified all five jobs; guarded source edits. New exact candidate CI pending; no local Qt execution or physical/owner acceptance claimed. Existing actual page-level confirmation dialogs, JSONL batch writers, hidden/generated row rules, sorting, playback and selection logic are unchanged. No configuration, training provenance, validation, model contract, six-tab topology, motor/STOP logic or inactive component changes. Focus indicators require native visual review; full keyboard/touch journey and comprehensive cross-component active-control audit remain open. R35 remains partial. No merge, promotion or deployment.
