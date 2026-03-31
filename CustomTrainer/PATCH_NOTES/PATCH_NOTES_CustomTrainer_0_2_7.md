# PATCH NOTES — CustomTrainer 0_2_7

## Scope
Patch-only update for CustomTrainer built forward from the delivered patch state **CustomTrainer_0_2_6** and the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
On the **Marking** tab:
1. allow dragging a selected box with **right-click drag**
2. make **Quick Deploy To Frames** help label and mark the frame inside the main canvas, instead of only showing prediction output in the side preview

## Problems addressed
1. Right-click already selected boxes, but moving a box with the mouse still required arrow keys.
2. Quick Deploy prediction results were mainly shown in the side preview/result browser, which meant the user still had to manually recreate those detections in the main labeling canvas.
3. The Marking workflow was missing a direct bridge from quick prediction into editable YOLO boxes on the active frame.

## Likely root cause
- `AnnotationCanvas` supported left-drag creation and right-click selection, but did not keep any right-button drag state for moving an existing box.
- The quick-deploy flow tracked saved preview images, but it did not keep a structured mapping of predicted boxes back to the original source frame for the main Marking canvas.

## Changes made

### 1) Added right-click drag box movement on Marking
- Reworked `AnnotationCanvas` so right-click still selects the smallest box under the cursor.
- If the right-click lands on a selected box, dragging with the right mouse button now moves that box directly.
- Left-drag box creation remains unchanged.
- Arrow-key nudging remains available and was not removed.

### 2) Quick Deploy now feeds the main Marking canvas
- Extended the internal prediction CLI to emit structured per-image / per-box prediction events in addition to the existing human-readable log lines.
- Marking now records predicted boxes by source image name while quick deploy is running.
- When quick prediction finishes for the current frame, the predicted boxes are loaded straight into the main Marking canvas as editable unsaved annotations.

### 3) Quick-deploy result browser now opens frames back in Marking
- Using the quick-deploy result selector / Prev Result / Next Result now focuses the matching source frame back in the session image list when possible.
- The main annotation canvas is then populated with that frame's predicted boxes so the user can adjust and save them immediately.
- The side preview remains available, but it is no longer the only place where quick-deploy results are usable.

### 4) Updated in-app wording / version
- Updated the visible window title to **CustomTrainer 0_2_7**.
- Updated shortcut/help text so it mentions **right-click drag** and the Marking-canvas quick-deploy workflow.
- Updated the README to describe the new behavior.

## Files changed
- `CustomTrainer/custom_trainer/ui/widgets/annotation_canvas.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_7.md`

## Exact behavior changed
Before this patch:
- right-click selected a box, but mouse dragging did not move it
- Quick Deploy predictions were mainly browsed in the side preview on Marking

After this patch:
- right-click selects a box and right-drag moves it
- Quick Deploy can load predictions back into the main Marking canvas so the user can refine and save them as YOLO labels
- the result browser can step through predicted frames and bring each one back into the main Marking canvas

## Verification actually performed
- Reviewed recent CustomTrainer patch notes (`0_2_6`, `0_2_5`, `0_2_4`, `0_2_3`) before patching to avoid rollback of:
  - startup-safe device probing
  - dataset / label preflight fixes
  - Marking shortcuts and per-class colors
  - top-level-only session scanning
  - Marking-only quick deploy
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Reviewed the modified quick-deploy event flow and Marking-page image-switch path to confirm predicted boxes can be loaded back into the editable canvas.

## Known limits / next steps
- Quick Deploy still does not auto-save predictions to disk; the loaded boxes remain editable until the user saves labels, which is safer for review.
- The source-image matching for quick-deploy results is based primarily on the original image path and filename; duplicate filenames across different sessions could still be ambiguous.
- A later patch could add a dedicated **Accept Predictions** button if the user wants explicit confirmation before loading predicted boxes into the canvas.
