# piTrainer Format and Style Guide

This document records the presentation decisions used by the V5 trainer UI. It is intended to stop future patches from styling individual tabs or panels differently by accident.

## Single source of truth

The main formatting source is:

```text
piTrainer/piTrainer/ui/formatting.py
```

The main stylesheet source is:

```text
piTrainer/piTrainer/ui/styles.py
```

Use these files first when changing spacing, font size, margins, splitter widths, button heights, tab sizes, panel minimum widths, or density rules. Avoid hard-coded visual numbers inside individual pages and panels unless the value is genuinely content-specific.

## Overall layout principle

The programme follows a left-to-right workflow:

```text
1 Data -> 2 Preprocess -> 3 Train -> 4 Validate -> 5 Export
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

- left: page number and page name, for example `1 of 5  Data`;
- below/near it: one short purpose sentence;
- right: compact green guide button, for example `Show: Load Selected`.

The banner guide button should not perform the action directly. It should reveal and focus the real green Next Step button inside the workflow panel.

## Workflow tabs

Use numbered workflow tabs inside dense control areas, for example:

```text
1 Load | 2 Review | 3 Manage
```

Use this pattern when a panel has multiple related work modes. Do not stack all modes vertically if that makes the panel hard to read.

The Data page uses this pattern twice:

- `Data Workflow`: `1 Load`, `2 Review`, `3 Manage`;
- `Data Review`: `1 Records`, `2 Plot`.

## Collapsible sections

Only detailed settings and fine-detail data tools should be collapsed by default.

Keep main action sections open by default, especially sections containing the page's Next Step button. The user should not need to search for the next action.

Good default-collapse candidates:

- advanced filters;
- overlay fine tuning;
- playback fine controls;
- merge/delete/management tools;
- training hyperparameter detail;
- export detail options.

Bad default-collapse candidates:

- session source selection;
- main preprocess action;
- start training action;
- run validation action;
- export action.

## Next Step buttons

The main workflow action button on each page should be obvious.

Expected style:

- green;
- full-width or visually wide;
- placed near the end of the relevant main action section;
- subtly pulsing/blinking only enough to guide attention;
- reachable from the compact banner guide button.

Expected examples:

- `Next Step: Load Selected`
- `Next Step: Confirm and Start Preprocess`
- `Next Step: Start Training`
- `Next Step: Run Validation`
- `Next Step: Export Selected Artifacts`

Do not make secondary buttons look like the main Next Step button.

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
- workflow and panel soft widths.

## Colour roles

Use the existing role system:

- `nextStep`: green main workflow action;
- `primary`: main blue action when it is not the workflow Next Step;
- `secondary`: normal actions;
- `danger`: destructive actions;
- `muted`, `hint`, `intro`, `statValue`, `summaryLine`, `summaryBlock`, `panelSubtitle`: label/text roles.

Do not add random one-off colour schemes inside panels.

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
2. Keep V5 features unless explicitly removed:
   - PiSD V7 data support;
   - V7 overlay redraw;
   - preprocessing/manual-drive fix;
   - training-start checks;
   - full-width splitters;
   - scrollable panel bodies;
   - compact guided banner;
   - green Next Step buttons;
   - unified formatting system.
3. Prefer updating `formatting.py`, `styles.py`, or `layout_widgets.py` before editing every panel individually.
4. Include patch notes in `piTrainer/PATCH_NOTES/`.
5. Do not reset user data or runtime config casually.

## Current V5 style decision summary

The trainer should look like a guided professional desktop workflow, not a dense engineering debug screen. Keep the path clear:

```text
Load data -> Preprocess -> Train -> Validate -> Export
```

Every tab and panel should support that flow with consistent sizing, clear grouping, readable spacing, and a visible next action.
