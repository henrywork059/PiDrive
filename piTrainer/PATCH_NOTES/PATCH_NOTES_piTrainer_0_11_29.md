# piTrainer 0.11.29 — Batch 4 / R35 desktop setup accessibility

Parent 2e33359 verified Linux 45736716777 (4/4) and Windows 45736716767 (1/1). Reviewed current main.py, component and root instructions, original R35 requirements, current widgets/styles/workflows and previous notes 0.11.28/27/26/25.

## Cause and changes
- ui/layout_widgets.py: shared CollapsibleSection QToolButton explicitly keyboard focusable, with accessible name and description. Existing checkable state, arrow, default expansion and click behavior retained.
- ui/styles.py: shared disclosure header focus border using existing theme token; no new colors or geometry changes.
- panels/preprocess/preprocess_config_panel.py and preprocess_filter_panel.py: distinct accessible names including paired min/max, threshold/copies and threshold/keep controls which otherwise share one visual form label.
- panels/export/export_options_panel.py and panels/data/playback_control_panel.py: accessible output destination/file name/artifact controls, Browse action and playback FPS; FPS label buddy.
- tests/test_validation_controls_r35.py: extend existing Linux and Windows native Qt suite with named fields, native range and playback keyboard interaction, disclosure Space/Tab/reverse Tab and stylesheet selector.
- version.py and shared regression gate notes updated.

## Verification and limits
Exact parent CI green; guarded source changes only, new exact CI pending. No local Qt execution claimed. No recipe defaults, applied preprocessing receipt, split, training, export, model, playback timing, configuration, data operations, layout topology or six-tab order changed. No inactive component edits. R35 remains partial pending broader active-control/touch audit. Owner visual and physical acceptance separate.
