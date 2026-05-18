# PATCH NOTES — piTrainer_0_3_21

## Request summary
- Update piTrainer to cooperate with the latest PiSD V7 recording data.
- Redraw the new PiSD road/path overlay from saved recording metadata instead of using only the old trainer-generated path preview.

## Cause / root cause
- PiSD `0_7_0` records Manual Drive overlay metadata in `manifest.json`, `records.jsonl`, and `labels.jsonl` using the retained schema name `PiSD_0_6_7_overlay_settings_v1`.
- piTrainer `0_3_20` already prioritised PiSD `labels.jsonl`, but it did not carry the overlay metadata into Data/Train/Validation views.
- The trainer preview still used its older quarter-ellipse path renderer, so it could not reproduce PiSD's V7 filled road corridor, tangent-normal road edges, perspective settings, corrected left/right direction, or user-entered overlay tuning numbers.
- Frame edit/delete/merge helpers still assumed older direct `records_root/session_name/records.jsonl` paths and did not reliably update PiSD dated sessions or compact `labels.jsonl` rows.

## Files changed
- `piTrainer/piTrainer/services/data/record_loader_service.py`
- `piTrainer/piTrainer/services/data/overlay_service.py`
- `piTrainer/piTrainer/services/data/edit_service.py`
- `piTrainer/piTrainer/services/data/delete_service.py`
- `piTrainer/piTrainer/services/data/merge_service.py`
- `piTrainer/piTrainer/services/data/preview_service.py`
- `piTrainer/piTrainer/services/train/worker.py`
- `piTrainer/piTrainer/services/validation/validation_service.py`
- `piTrainer/piTrainer/panels/data/overlay_control_panel.py`
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
- `piTrainer/piTrainer/panels/train/train_epoch_review_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_3_21.md`

## Exact behavior changed
- `labels.jsonl` remains the primary PiSD training source, but piTrainer now also imports:
  - `overlay_settings`
  - `overlay_schema_version`
  - `overlay_settings_source`
  - `has_overlay_settings`
- If an individual row does not contain overlay settings, the loader falls back to session-level `manifest.json` overlay metadata.
- Data preview now defaults to a `Show PiSD V7 road guide` overlay.
- The PiSD V7 road guide is rendered in Python/QPainter using the same geometry logic as PiSD's browser overlay:
  - sampled kinematic-style centre path
  - tangent-normal left/right road boundaries
  - filled road corridor surface
  - perspective projection values
  - corrected steering left/right direction from the shared PiSD helper
  - recorded overlay settings such as curve strength, width, horizon, perspective depth, sample count, wheelbase, curvature tuning, and taper values
- The older trainer path preview is preserved as `Show legacy trainer path (debug)` instead of being removed.
- Data Image Preview now shows a small overlay metadata status line so the user can see whether the frame is using recorded PiSD settings or PiSD V7 defaults.
- Train epoch best/worst frame review now carries overlay settings forward and draws target/predicted comparison using the PiSD road-guide renderer.
- Validation frame review now carries overlay settings forward and draws target/predicted comparison using the PiSD road-guide renderer.
- Record Preview includes source and overlay metadata columns when available, making PiSD `labels.jsonl` loading more visible.
- Frame editing now resolves dated PiSD session paths through `resolve_session_dir()` and updates both `labels.jsonl` and `records.jsonl` when both are present.
- Frame deletion now resolves dated PiSD session paths and removes matching rows from both `labels.jsonl` and `records.jsonl` when both are present.
- Merge Sessions now loads source rows through the PiSD-aware loader, preserves overlay metadata, and writes both `records.jsonl` and `labels.jsonl` for the merged session.

## Compatibility notes
- Existing older piTrainer/PiCar sessions without overlay metadata still load.
- If no saved overlay metadata is found, previews use PiSD V7 default overlay values.
- Training inputs remain unchanged: the model still trains on image, steering, and throttle only.
- Overlay metadata is used for visual redraw/review only; it is not fed into the model.
- The old debug overlays remain available: speed bar, steering bar, steering arc, legacy path, and drive arrow.
- Single-capture/snapshot buckets remain excluded from normal session discovery, matching the `0_3_20` behavior.

## Rollback-risk check
- Checked latest trainer patch note `0_3_20` and previous available patch notes `0_3_18`, `0_3_17`, and `0_3_16`.
- Preserved PiSD dated-session and `labels.jsonl` priority support from `0_3_20`.
- Preserved default docking/layout organization from `0_3_18`; no dock layout files were changed.
- Preserved earlier path-preview/debug overlay work from `0_3_16` and `0_3_17` by keeping it as the optional legacy path overlay.
- Did not change TensorFlow training data shape, model architecture, validation metrics, export flow, shortcuts, or docking behavior.

## Verification actually performed
- Ran `python3 -m compileall` on the full `piTrainer` package after patching.
- Created a temporary PiSD V7-style sample folder with:
  - `recordings/2026-05-18/YYYYMMDD_HHMMSS_manual_drive_xxxxxxxx/frames/`
  - `manifest.json` containing overlay metadata
  - `labels.jsonl` containing `frame`, `relative_file`, `steering`, `throttle`, `timestamp_utc`, `source_frame_seq`, `overlay_settings`, and `overlay_schema_version`
  - `records.jsonl` containing the full debug record and nested `training_label`
- Verified `list_sessions()` finds the dated PiSD session from a PiSD project root.
- Verified `load_records_dataframe()` loads from `labels.jsonl`, resolves the image path, and keeps overlay metadata as a dictionary.
- Verified `build_filtered_dataframe()` keeps the usable PiSD training row.
- Verified `update_frame_controls()` updates both `labels.jsonl` and `records.jsonl` for a PiSD dated session.
- Verified `delete_frame_from_session()` removes matching rows from both `labels.jsonl` and `records.jsonl` and deletes the image file.
- Created a second temporary two-session PiSD V7 dataset and verified `merge_sessions()` produces a merged session with both `records.jsonl` and `labels.jsonl`, preserving overlay metadata.

## Verification not performed
- Full PySide6 GUI smoke rendering was not run in this container because PySide6 is not installed here.
- Full TensorFlow model training/validation was not run in this container.
- Real PiSD V7 recording data from hardware was not available beyond the package source and generated sample data.

## Known limits / next steps
- On the real PC environment with PySide6 installed, open the Data tab and visually compare a PiSD V7 recorded frame against the PiSD browser overlay for the same steering/throttle/settings.
- If exact pixel-perfect matching is needed later, add a small shared geometry test fixture between PiSD JavaScript and piTrainer Python using saved expected point coordinates.
