# piTrainer Format and Style Guide

This document records the presentation decisions used by the V8 trainer UI. It is intended to stop future patches from styling individual tabs or panels differently by accident.

## V8 stable baseline note

V8 (`piTrainer_0_8_0`) promotes the accepted V7 patch line through `piTrainer_0_7_3` into the latest full baseline. Future patches should build forward from V8 as `0_8_x` without rolling back accepted data layout, preprocessing, training, validation, export, table, style, soft-hide, generated-data visibility, and startup version-gate behaviours.

The previous V7 baseline (`piTrainer_0_7_0`) promoted accepted V6 work through `piTrainer_0_6_20`. V8 keeps that V6/V7 work and adds the accepted V7.1, V7.2, and V7.3 patch behaviours.

## Single source of truth

The main formatting source is:

```text
piTrainer/piTrainer/ui/formatting.py
```

The main stylesheet source is:

```text
piTrainer/piTrainer/ui/styles.py
```

Use these files first when changing spacing, font size, margins, splitter widths, button heights, tab sizes, panel minimum widths, or density rules. Use `piTrainer/piTrainer/ui/theme.py` first when changing colours for widgets or plots. Avoid hard-coded visual numbers or colours inside individual pages and panels unless the value is genuinely content-specific.

## Overall layout principle

The programme follows a left-to-right workflow:

```text
1 Data -> 2 Preprocess -> 3 Train -> 4 Validate -> 5 Export -> 6 Export Validation
```

Each page should use a full-width splitter workspace. Visible sections should fill the window width. Users should change proportions by dragging splitter handles, not by pulling hidden right-side dock areas open.

Preferred page structure:

```text
[Workflow controls] | [Main review/work area] | [Visual preview or output area]
```

For two-section pages:

```text
[Workflow controls] | [Main result/log/export area]
```

## Splitters and resizing

Use central splitter presets from `formatting.py` instead of one-off sizes.

Current intent:

- workflow controls get enough width for buttons and forms;
- record tables, plots, previews, and logs get the larger central/right space;
- splitter panels may be reduced by the user;
- when a panel becomes narrower than its readable content width, the panel body should show a horizontal scrollbar only when needed.

Do not reintroduce many stacked dock panels on the same side. That was the main readability issue in earlier layouts.

## Scroll behaviour

Panel bodies should remain reachable at smaller window sizes.

Expected behaviour:

- vertical scrollbars appear when content is taller than the panel;
- horizontal scrollbars appear only when the user reduces a panel below its readable width;
- panel headers stay visible when the body scrolls;
- workflow sidebars can scroll without forcing the whole main window to become oversized.

Use shared helpers from:

```text
piTrainer/piTrainer/ui/layout_widgets.py
```

## Page banner

The page banner should stay compact. It should explain the current page, but it must not consume too much vertical space.

Expected banner format:

- left: page number and page name, for example `1 of 6  Data`;
- below/near it: one short purpose sentence;
- right: compact green guide button, for example `Load Selected`.

The banner guide button should not perform the action directly. It should reveal and focus the real green action button inside the workflow panel.

## Workflow tabs

Use numbered workflow tabs inside dense control areas, for example:

```text
1 Load | 2 Manage | 3 Review
```

Use this pattern when a panel has multiple related work modes. Do not stack all modes vertically if that makes the panel hard to read.

The Data page uses this pattern twice:

- `Data Workflow`: `1 Load`, `2 Manage`, `3 Review`;
- `Data Review`: `1 Records`, `2 Stats`, `3 Plot`.

Keep the record table first in `Data Review`, because row selection drives the image preview and deletion workflow. The record table should support multi-row selection for batch frame hiding/deletion and batch label editing, `frame_id` should remain the first visible column, and the table should keep the first column visible after multi-selection instead of horizontally jumping to later columns. Keep dataset statistics inside `Data Review`, not in the loading workflow. Keep playback controls directly underneath the image preview so frame playback stays visually tied to the currently displayed frame. Keep Frame Filter in the Manage workflow beside Data Control. Keep Bulk Edit Selected Frames in the Review workflow so users can apply either steering-only or speed-only changes to the selected Record Preview rows after explicit warning confirmation. Keep Merge Sessions in the Review workflow, but collapsed by default so normal review remains compact. Do not reintroduce a separate generic `Data Actions` panel; place each action beside the thing it affects, such as refresh/load in `Session Source`, hide/delete in `Data Control`, bulk steering/speed edits in Review, and filter clearing in `Frame Filter`.


## Preprocess workflow

The Preprocess page should favour the common path over the expert path. The accepted V6.11 layout is:

```text
[Preprocess Workflow: 1 Auto | 2 Settings] | [Preprocess Review: 1 Preview | 2 Log]
```

`1 Auto` is the default path for most users. It contains the source summary and `Quick Preprocess` panel. The green `Auto Preprocess Active Data` button loads the recommended defaults and applies preprocessing in one action. Recommended defaults include one horizontal flip copy for every active frame, with steering inverted on the flipped copy and speed/throttle preserved. Flipped rows keep source steering metadata so the training and validation paths can guard against stale or wrongly signed labels. Amber setup buttons are available for `Use Recommended Defaults` and `Preview Current Recipe` when the user wants to check row counts first.

`2 Settings` is optional and should contain custom controls only. Keep source/mode and output image size visible. Horizontal flip augmentation is part of the recommended default recipe, but its checkbox should remain in the collapsed augmentation section so the normal workflow stays simple. Keep detailed thinning, range filters, balancing, turning boost, and colour-variant settings collapsed by default. More advanced settings should be deeper and more collapsed, not spread across the first visible workflow.

Preprocess logs should not take vertical space from the main preview by default. Keep Preview and Log as tabs in the review area so the preview/result text remains the main thing users see after preprocessing.

Horizontal flip safety rule:

- flipped rows must set `aug_flip_lr=True`;
- flipped rows must invert `steering` from the original/source steering;
- flipped rows must preserve `throttle`/speed;
- training and validation loaders must apply the shared flip-label guard before using labels;
- training and validation loaders must apply the image flip whenever `aug_flip_lr` is true;
- train epoch review and validation frame review must also display the flipped image when `aug_flip_lr` is true, so the preview image, label, prediction, and overlay all refer to the same orientation;
- validation/image preview must not show or score an unflipped image against an inverted steering label;
- older saved datasets missing `source_steering` should be repaired from a matching unflipped `source_frame_id` where possible, otherwise marked with a warning instead of silently guessed.

Synthetic-row identity rule:

- generated rows must not reuse the original source `frame_id`;
- every synthetic row must have its own `frame_id` beginning with `s_`;
- every synthetic row should keep `source_frame_id`, `is_synthetic=True`, and `synthetic_variant` metadata;
- this applies to horizontal flip rows, colour-variant rows, and turning boost copies.

## Collapsible sections

Only detailed settings and fine-detail data tools should be collapsed by default.

Keep main action sections open by default, especially sections containing the page's main action button. The user should not need to search for the next action.

Good default-collapse candidates:

- advanced filters;
- overlay fine tuning;
- training hyperparameter detail;
- export detail options.

Data Control is an exception: it is a destructive management tool, but the user requested it to stay expanded by default so frame hiding/deletion is easy to find. The delete action should now be a traceable soft-delete: add hidden flags to matching `labels.jsonl` / `records.jsonl` rows and keep image files in place. The hide/delete action should use an explicit confirmation checkbox in Data Control. Once that checkbox is ticked, repeated hide/delete operations should not show a separate confirmation popup every time. Bulk Edit Selected Frames is also expanded in Review so the batch steering/speed workflow is visible, but it must keep its own overwrite-warning checkbox and a final confirmation dialog before writing labels.

Bad default-collapse candidates:

- session source selection;
- main preprocess action;
- start training action;
- run validation action;
- export action.


## Hidden/deleted frame handling

Frame deletion should be fast and traceable. Do not physically remove selected images or rewrite JSONL files by dropping rows. Instead, selected frames should be hidden from training by setting traceable flags such as `hidden_from_training`, `piTrainer_hidden`, `deleted_by_pitrainer`, `hidden_at_utc`, and `hidden_reason` on the matching JSONL records. If a `training_label` object is present, mirror the same flags there too.

Expected behaviour:

- selected rows disappear from the active Record Preview after hide/delete;
- the source JSONL records remain in place for audit/recovery;
- the image files remain on disk;
- future session loads skip hidden records;
- preprocessing, training, validation, and TensorFlow dataset creation apply a final hidden-row guard before using rows.

This means the Delete key and Data Control button are user-facing delete/hide actions, but the implementation is a soft delete. Do not roll this back to physical file removal unless the user explicitly asks for a permanent purge tool.

## Batch frame editing

Bulk edits are intentionally separate from single-frame edits in the Image Preview panel.

Expected behaviour:

- users select one or more rows in `Data Review > 1 Records`;
- `Data Workflow > 3 Review > Bulk Edit Selected Frames` shows the selected-frame count;
- steering and speed are applied with separate buttons;
- `Apply Steering Only` must only change steering while preserving each frame's existing speed/throttle;
- `Apply Speed Only` must only change speed/throttle while preserving each frame's existing steering;
- the user must tick the bulk overwrite confirmation checkbox before buttons are enabled;
- a final warning confirmation dialog must appear before values are written to `labels.jsonl` / `records.jsonl`;
- bulk edits should update the loaded DataFrame, stats, plot, and preview without requiring a full app restart;
- bulk edits should use a batch JSONL service that groups selected rows by session and scans each `labels.jsonl` / `records.jsonl` file once. Do not call the single-frame edit function once per selected row, because that repeatedly rewrites the same metadata files and becomes slow on large sessions.

Do not combine steering and speed into one bulk-apply button unless the user explicitly asks. One-at-a-time application reduces accidental overwrites.

## Main action buttons

The main workflow action button on each page should be obvious without using the old label prefix.

Expected style:

- green;
- full-width or visually wide;
- placed near the end of the relevant main action section;
- subtly pulsing/blinking only enough to guide attention;
- reachable from the compact banner guide button.

Expected examples:

- `Load Selected`
- `Auto Preprocess Active Data`
- `Start Training`
- `Run Validation`
- `Export Selected Artifacts`

Do not make secondary buttons look like the main action button.

Visible action labels should not include the old `Next Step:` prefix, and compact banner guide labels should not include the old `Show:` prefix.

## Visual hierarchy

Use consistent roles rather than local styling.

Recommended hierarchy:

1. Main workflow tabs at the top.
2. Compact page banner.
3. Splitter panel titles.
4. Workflow sub-tabs.
5. Collapsible section headers.
6. Form labels, hints, tables, and logs.
7. Secondary actions.

Avoid competing large headings inside the same area.

## Tables, lists, and logs

Tables should be readable and stable:

- alternating rows enabled;
- row headers hidden unless needed;
- horizontal headers visible and interactive;
- columns should not collapse to unreadable widths;
- horizontal scroll should be allowed when necessary.

Logs should wrap or scroll according to the panel type. Logs should not force the page to expand beyond the window.

## Forms and inputs

Forms should use the shared form layout behaviour:

- labels left-aligned;
- fields grow where possible;
- long rows may wrap;
- spacing comes from the active density profile.

Use `standardize_form_layout()` from `formatting.py` for new forms.


## Train page layout

The Train page should use a three-column workspace:

```text
[Training Workflow] | [Training History / Log] | [Epoch Frame Review]
```

The rightmost frame-review column keeps best/worst epoch frames visually separate from controls and loss curves. Frame review cards should be stacked vertically so the right column stays readable at normal laptop widths.


## Validation page layout

The Validation page should use a three-column workspace:

```text
[Validation Workflow] | [Validation Plot / Log] | [Validation Frame Review]
```

The left column keeps model/dataset/run controls and the result summary. The middle column keeps validation plots and logs. The right column keeps frame-level validation review so users can inspect bad predictions without the preview pushing plots/logs down.

## Export Validation page layout

The Export Validation page should sit directly after Export as the final workflow page. It should use the same three-column validation format:

```text
[Export Validation Workflow] | [Export Validation Plot / Log] | [Export Validation Frame Review]
```

This page is specifically for diagnosing exported deployment behaviour. It must load a `.tflite` file through a real TensorFlow Lite interpreter, not through the in-memory Keras model, and it should show prediction output ranges so narrow steering/speed output can be compared against normal model validation. The Export page should link the newest created `.tflite` path into Export Validation when an export succeeds, while still allowing the user to browse to another deployed `.tflite` file manually.



## Export workflow and TensorFlow converter messages

The Export page should make the action button immediately visible. Keep the `Export Workflow` tabs ordered as:

```text
1 Export | 2 Status
```

The `1 Export` tab should contain `Export Actions` above `Export Options`, so the green `Export Selected Artifacts` button is visible before status/detail panels. The model readiness summary should remain available in `2 Status`, but it should not be the first thing users see on the final workflow page.

The Export page should report export success in user-facing terms, not by leaving raw TensorFlow converter internals in the PowerShell window. Expected export log behaviour:

- list each created artifact with file type, full path, and size;
- summarise non-fatal TensorFlow/Keras/TFLite converter chatter instead of displaying temporary SavedModel endpoint dumps;
- keep the size-optimised TFLite option clear that it reduces model size while keeping float32 input/output for the current PiDrive runtime;
- keep warnings/errors visible only when they affect the actual export result.

The `.keras` file is the main retrain/reload artifact. The `.tflite` file is the deployment artifact. When size optimisation is enabled, the file name may still include `_int8`, but the current app should explain that PiDrive-compatible float32 input/output is intentional rather than an export failure.

## Training device / GPU support

Training should default to `Auto (GPU if available)`. This lets TensorFlow use a compatible GPU when the installed TensorFlow build and drivers expose one, while continuing on CPU when no GPU is visible. `CPU only` should hide GPU devices before model/dataset creation when possible, and `GPU only` should fail early with a clear log message if TensorFlow cannot detect a GPU.

Keep TensorFlow imports inside the training worker so the UI starts even when TensorFlow or GPU support is missing. The worker should log which device mode was requested and whether GPU devices were detected.


## TensorFlow log handling

TensorFlow should still be imported lazily by training, validation, and export paths rather than on the UI thread at app startup. Set `TF_CPP_MIN_LOG_LEVEL` before any TensorFlow import so normal oneDNN/CPU feature INFO messages do not flood the PowerShell console. Do not silently set `TF_ENABLE_ONEDNN_OPTS=0`; users can still choose that manually if they specifically need to disable oneDNN optimisations for repeatability.

## Density profiles

The UI supports responsive density profiles:

- compact;
- comfortable;
- spacious.

The active profile is selected from the main window width. Change density values in `DENSITY_PROFILES` rather than patching individual widgets.

Typical density-controlled items:

- base font size;
- banner title size;
- button/input minimum heights;
- page and panel margins;
- form spacing;
- scrollbar width;
- splitter handle width;

Current V6.6 sizing rule: splitter handles stay slim, while scrollbars are about 30% thicker than V6.5 so they remain easier to see and grab after user review.
- workflow and panel soft widths.

## Colour roles

The colour source of truth is:

```text
piTrainer/piTrainer/ui/theme.py
```

The Qt stylesheet should reference semantic colour tokens through `styles.py` / `formatting.py`, and matplotlib plots should use `theme_color()` instead of local hex values. The palette follows these practical rules: high text contrast, neutral dark surfaces, blue/cyan for navigation and focus, green for main actions, yellow amber for prerequisite/setup actions that normally need to happen before a main green action, and red/pink only for destructive or error states.

Use the existing role system:

- `nextStep`: large green main workflow action;
- `primary`: green main action inside a panel when the button is not the large guided workflow button;
- `secondary`: normal supporting actions;
- `amber`: prerequisite/setup actions that usually happen before the main action, such as Browse, Refresh, Preview Preprocess, Prepare Split, or Browse Model; the accepted shade is yellow-forward amber with dark text;
- `danger`: destructive actions;
- `muted`, `hint`, `intro`, `statValue`, `summaryLine`, `summaryBlock`, `panelSubtitle`: label/text roles.

Do not add random one-off colour schemes inside panels. If a new colour is needed, add a semantic token to `theme.py`, then consume it through the central stylesheet or plotting helpers.


## Sliders

Steering and speed sliders should not use the same fill logic when their value ranges are different.

- Speed is a 0-to-1 value, so a normal left-to-right fill is correct.
- Steering is a -1-to-1 value, so neutral steering is in the middle. The Edit Steering slider and bulk steering slider should fill outward from the centre marker, not from the left edge.

Use the shared slider helper in `piTrainer/piTrainer/ui/sliders.py` for centred-fill steering sliders rather than patching local paint logic into each panel.


## Record Preview navigation and edit responsiveness

Record Preview must stay visually anchored on the first visible column. Use a simple read-only `QTableView` with a small `QAbstractTableModel`, not item-by-item `QTableWidget` current-cell logic. Header sorting is allowed, but it must stay inside the model and preserve an explicit view-row to source-dataframe-row mapping so selection, preview, bulk edit, and hide/delete operations keep targeting the correct frames. The default sort should be `frame_id` ascending. Keep the visible columns short and stable, with `frame_id` as the first column. Multi-row selection, Select All, and keyboard movement should not leave the table horizontally scrolled to the second column. Keep current-index normalisation/scrollbar anchoring inside the preview panel rather than duplicating it in page code. Normal mouse selection should not force the selected row into the vertical middle of the table; use ensure-visible scrolling only for programmatic navigation such as Up/Down cycling, playback, or focus-by-identity.

When the Record Preview table has focus, Up and Down should cycle through frame rows. Down moves to the next frame and wraps from the last row to the first; Up moves to the previous frame and wraps from the first row to the last.

Single-frame edits from Image Preview should feel immediate. Do not rebuild the full table after every small steering/speed adjustment unless an active speed/steering filter means the edited row may need to disappear. Prefer targeted row updates, queued/debounced JSONL writes that do not block clicking into the next frame, cached JSONL parsing for repeated same-session edits, and delayed plot refresh. When a queued edit commits after the user has selected another row, update the edited row in place without stealing the current selection.

Bulk Edit should keep a setup-style `Select All Visible Frames` button inside the Bulk Edit panel so users can quickly select every currently displayed frame before applying one steering-only or speed-only edit.


## Training defaults

Train Config should open with defaults that work for most small PiSD datasets without requiring extra choices:

- split mode: `Random rows`;
- default epochs: `100`;
- validation ratio: keep the existing default ratio unless the user asks to change it;
- training device: `Auto (GPU if available)`.

`By session` and `Sequential rows` remain available as advanced/manual choices, but they should not be the default. Random rows usually gives the user an immediate train/validation split even when only one session is loaded.

## Record Preview table model rule

The Record Preview list should stay intentionally simple. The accepted V6.14 pattern is:

- `QTableView` for the view;
- one small read-only `QAbstractTableModel` for the preview rows;
- `frame_id` as column 1;
- header sorting enabled through the model, with default sort by `frame_id`;
- an explicit source-row mapping so sorted table rows still edit/hide/delete the correct records;
- a short fixed column order: `frame_id`, `session`, `steering`, `throttle`, `mode`, `ts`;
- row selection maps directly to the active preview dataframe row;
- horizontal anchoring resets the scrollbar to the first column without vertically centring normal mouse selections.

Do not reintroduce `QTableWidget` item-based mapping, per-cell current selection, or automatic column resizing during every selection change. Those behaviours caused intermittent horizontal jumps to later columns and made multi-select harder to reason about.

## Version display

The visible app version is controlled by:

```text
piTrainer/piTrainer/version.py
```

Patch releases should update:

- `APP_VERSION`;
- `PATCH_VERSION`;
- window title/status version text generated from those values.

## Patch guidance

When making future UI patches:

1. Check the latest app state and latest patch notes.
2. Keep V6 features unless explicitly removed:
   - PiSD V7 data support;
   - V7 overlay redraw;
   - preprocessing/manual-drive fix;
   - training-start checks;
   - full-width splitters;
   - scrollable panel bodies;
   - compact guided banner;
   - green action buttons;
   - unified formatting/style/colour system.
3. Prefer updating `formatting.py`, `styles.py`, or `layout_widgets.py` before editing every panel individually.
4. Include patch notes in `piTrainer/PATCH_NOTES/`.
5. Keep `piTrainer/AGENTS.md` aligned with current baseline and anti-rollback rules when workflow rules change.
6. Do not reset user data or runtime config casually.

## Current V8 style decision summary

The trainer should look like a guided professional desktop workflow, not a dense engineering debug screen. Keep the path clear:

```text
Load data -> Preprocess -> Train -> Validate -> Export -> Export Validation
```

Every tab and panel should support that flow with consistent sizing, clear grouping, readable spacing, colour roles that match the action meaning, slim splitter/scroll controls, and a visible next action.

## V7.2 Data Review synthetic-row visibility

Data Review is the raw-frame review/editor. Preprocess can create generated rows such as horizontal flips, colour variants, and turn-boost copies, and those rows stay available for Train and Validate. However, Record Preview should hide generated/synthetic rows by default so the Data page remains focused on original source frames.

The accepted behaviour is:

- generated rows keep trace metadata (`frame_id` starting with `s_`, `source_frame_id`, `is_synthetic=True`, and `synthetic_variant`);
- Data Review hides those generated rows by default;
- Train and Validate still use generated rows unless they have hidden/delete flags;
- the Validation `Edit in Data` button redirects generated rows to the matching original source frame, usually by `source_frame_id`;
- if no safe source frame can be found, the app should fail gracefully rather than editing a hidden generated copy silently.

## V7.3 startup version access gate

PiTrainer can be release-controlled by a small public JSON manifest hosted in the PiDrive GitHub repo. This is a soft version gate for packed releases, not strong copy protection. It is designed to let the project owner disable old builds by editing one online manifest file.

Local config:

```text
piTrainer/config/version_gate.json
```

Startup implementation:

```text
piTrainer/piTrainer/security/version_gate.py
```

Online manifest used by the V7.3/V8 release gate:

```text
https://raw.githubusercontent.com/henrywork059/PiDrive/refs/heads/main/release_control/pitrainer_access.json
```

Expected manifest shape:

```json
{
  "app": "PiTrainer",
  "latest": "0.8.0",
  "allowed_versions": ["0.8.0"],
  "blocked_versions": ["0.7.0", "0.7.1", "0.7.2", "0.7.3"],
  "message": "This PiTrainer version is no longer enabled. Please update to the latest version.",
  "support_message": "Please contact the project owner for the newest PiTrainer build."
}
```

When the gate is enabled, the app checks this manifest before opening the main window. If the current `APP_VERSION` is blocked or is missing from a non-empty `allowed_versions` list, the app displays a clear blocking message and exits. Network access uses a short timeout and caches successful checks for the configured cache duration.

For PyInstaller releases, make sure the config file is bundled or copied beside the executable, for example by adding the config folder as PyInstaller data or by shipping a `config/version_gate.json` folder next to `PiTrainer.exe`.

For V8 packages, update the online manifest before testing or distributing the release so `allowed_versions` includes `0.8.0`. If the manifest still only allows `0.7.3`, the V8 app will correctly block itself at startup when the version gate is enabled.

