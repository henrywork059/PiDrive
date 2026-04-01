# CustomDrive 0_3_7 Patch Notes

## Request summary
Optimize the GUI AI settings page so it is easier to use for the current object-detection workflow.

Requested changes:
- clean up the AI settings layout,
- remove unused boxes/buttons,
- and allow the overlay update frequency to be changed from the page.

## Anti-rollback review performed
Before patching, I checked:
- the reconstructed current CustomDrive code state built forward from `CustomDrive_0_3_0` plus accepted `0_3_1` to `0_3_6`,
- the latest patch note: `0_3_6`,
- the previous three recent notes: `0_3_5`, `0_3_4`, and `0_3_3`.

That review was used to avoid rolling back:
- the current AI backend / overlay path,
- the copyable AI debug snapshot/history behavior,
- the accepted every-N-frame overlay cadence behavior,
- the recent arm fixes,
- and the current GUI entrypoint/layout direction.

## Root cause
There were three UI/config problems.

### 1) The AI page still exposed mission-only controls even though the current workflow is detector-only
The page still showed:
- mission target label,
- drop-zone label,
- and a mission-oriented explanatory note.

That made the AI page noisier than necessary for the current debugging/deployment workflow and did not match the user’s current request to ignore mission logic for now.

### 2) The page still carried redundant manual buttons
The page still had both:
- `Refresh Models`, and
- `Save AI Settings`.

Those were not pulling their weight because:
- opening the modal already refreshes the model list,
- upload/delete/deploy flows already refresh relevant model state,
- and the runtime tuning fields were already being auto-saved from the frontend.

So the page had extra controls that increased clutter without adding a distinct useful action.

### 3) The real overlay cadence control existed in backend config, but the page did not expose it
The backend already supported:
- `overlay_frame_skip`

and the accepted overlay behavior was already based on an every-N-frame inference cadence, but the GUI only exposed `max_overlay_fps`.

That meant the user could not directly adjust the actual frame-skip frequency from the page even though the backend already supported it.

## Files changed
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_7.md`

## Exact behavior changed

### 1) The AI modal layout is now split into clearer sections
The page is now grouped into:
- **Model**
- **Overlay**
- **Debug**

This reduces scrolling clutter and makes it easier to find the actions relevant to:
- uploading/deploying models,
- tuning live overlay behavior,
- and inspecting AI debug output.

### 2) Mission-only controls were removed from the AI page, but not from backend config
The following controls were removed from the page:
- mission target label
- drop-zone label

This was done because the current request was explicitly not to follow mission logic for now.

Important: this patch does **not** delete those settings from backend/config support. It only removes them from the current AI page so future mission work is not silently broken.

### 3) Redundant AI buttons were removed
The following buttons were removed from the AI modal:
- `Refresh Models`
- `Save AI Settings`

The page now relies on:
- automatic model refresh when the modal opens,
- automatic state refresh after upload/delete/deploy actions,
- and auto-save for overlay/tuning fields.

### 4) The real overlay cadence can now be changed from the page
A new field is now exposed in the AI settings modal:
- **Refresh every N frames**

This writes through to backend `overlay_frame_skip` support.

Examples:
- `1` = run inference every frame
- `5` = run inference every 5 preview frames

This matches the accepted overlay design much more directly than only showing an overlay FPS box.

### 5) Model-select fields are now clearer about when Deploy is required
Model-related settings now keep the page focused on the actual model workflow.

Changing:
- model
- labels file
- input size

now shows a clearer reminder that those changes take effect after **Deploy**.

### 6) Overlay/tuning settings still auto-save
The following fields still auto-save from the GUI:
- backend
- overlay enabled
- refresh every N frames
- confidence threshold
- IoU threshold

This preserves the accepted quick-tuning behavior while removing the redundant explicit save button.

### 7) Backend routes now preserve hidden mission settings instead of overwriting them
Because the mission fields were removed from the page, the backend deploy/config routes were updated so that when those fields are omitted, the existing saved values are preserved instead of being reset to defaults.

This prevents a UI cleanup from accidentally rolling back future mission-related config.

### 8) `overlay_frame_skip` is now part of the normalized AI config schema
The manual config schema/default normalization now includes:
- `overlay_frame_skip`

So the cadence setting is now safely clamped/persisted through the same config path as the rest of the AI runtime settings.

### 9) GUI asset/version line bumped forward
The GUI app version string was updated to `0_3_7` so the browser is more likely to fetch the new frontend assets after patching.

## Verification actually performed
- Reconstructed the active CustomDrive code state forward from:
  - `CustomDrive_0_3_0.zip`
  - `CustomDrive_0_3_1_patch.zip`
  - `CustomDrive_0_3_2_patch.zip`
  - `CustomDrive_0_3_3_patch.zip`
  - `CustomDrive_0_3_4_patch.zip`
  - `CustomDrive_0_3_5_patch.zip`
  - `CustomDrive_0_3_6_patch.zip`
- Re-read the recent patch notes listed above before editing.
- Inspected the real current AI settings page in:
  - `custom_drive/gui_web/templates/index.html`
  - `custom_drive/gui_web/static/app.js`
  - `custom_drive/gui_web/static/styles.css`
- Inspected the current AI config/deploy routes in:
  - `custom_drive/gui_control_app.py`
- Inspected the current AI config normalization in:
  - `custom_drive/manual_control_config.py`
- Ran:
  - `python -m compileall custom_drive`
- Ran JavaScript syntax check on:
  - `custom_drive/gui_web/static/app.js`

## Known limits / next steps
- I did **not** claim a live browser visual test in this container.
- This patch focuses on AI-page cleanup and cadence control. It does not change the underlying detector math or Pi camera pipeline.
- The backend still keeps `max_overlay_fps` support internally; this patch simply stops exposing that older control on the main AI page because the user asked for the real overlay frequency control instead.
- Mission labels remain in config/backend support and can be surfaced again later if mission workflow returns to the foreground.
