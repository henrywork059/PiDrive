# piTrainer 0.11.32 — Consolidated R35 desktop accessibility

## Verified baseline
Exact parent 20be5ad4446d8350726abd8645f09a0a0a3b5fed, Linux 45785643038 4/4 and Windows 45785642998 1/1, 36/36 Chromium, PiSD Node 27/27 and standard 63/63, PiServer Node 33/33, Windows Qt 15/15, manifests 7/7 and packages 11/11, forward dry runs 5/5/8. Actual artifacts 15100736466 and 15099279255 inspected in preceding review. Reviewed real launcher, shared widgets, canonical R35 and notes 0.11.31/30/29/28; next version absent on main, integration and matching branches.

## Changes
- piTrainer/ui/styles.py: retain semantic green palette, dark text on bright green primary/recommended/banner actions and saved/preprocessing done labels (8.27:1 default, 9.80:1 hover), white on dark green pressed (5.02:1), including highlighted pressed states; visible task-result focus border.
- piTrainer/ui/layout_widgets.py: restore disclosure header focus only if collapsing focused descendant; preserve unrelated focus and existing expansion state.
- piTrainer/panels/common/log_panel.py: contextual accessible name/description, strong focus and native Tab exit from read-only text.
- piTrainer/panels/common/task_progress_panel.py: named progress and synchronized current-step description across pending and terminal states; keyboard-selectable result/output paths. Actual task execution semantics unchanged.
- tests/test_shared_accessibility_r35.py: three native Qt regression cases for contrast across densities, disclosure focus continuity, log Tab and progress/result keyboard access. piTrainer/version.py: version markers.
- Shared Linux and Windows CI add syntax gates and new regression coverage.

## Verification and limits
Full changed Python files compiled locally with candidate Git blob hash matching; numeric contrast checked locally. Combined candidate browser/native Qt/package gate pending. No local Chromium or native Qt execution. No config, task, data, training, export, layout persistence, drive/motor, STOP, authorization or command lease changes. R35 partial; broader contrast/custom themes, screen readers, native touch/hardware/owner acceptance remain. No merge, stable promotion, deployment or Batch 6 advancement.

## Revision B — consolidated data-review continuation

- Actual Data selection now feeds a bounded read-only bulk-edit preview (two representative source session/frame identities, exact selected count, current and proposed steering/throttle, unknown labels retained). Slider/spin updates refresh the preview without mutation. Count-only resets clear stale identities. Existing overwrite checkbox, fresh selection lookup, explicit final confirmation, one-field writes and source identity rules remain unchanged.
- Files: piTrainer/panels/data/bulk_edit_panel.py, piTrainer/pages/data_page_filter_edit.py, tests/test_review_context_ux61.py. Existing comparison and contextual F1 help preserved; no shortcut, saved setting or layout-persistence changes. New native test covers duplicate frame IDs in separate sessions, missing labels, live values, clearing, no writes and unchanged confirmation gate. Native execution pending; no acceptance claimed.
- Forward from 50813d30b675062808fcf988a29536b40f8f4484; notes 0.11.32/31/30/29 reviewed in this cycle. No version allocation, stable promotion or deployment.
