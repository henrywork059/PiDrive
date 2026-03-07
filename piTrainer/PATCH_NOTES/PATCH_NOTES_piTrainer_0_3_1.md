# PATCH NOTES — piTrainer_0_3_1

## What changed
- Added a new **Merge Sessions** panel on the Data page.
- Added a dedicated merge service to combine multiple selected sessions into one new session folder.
- Added session selection helper support so the new merged session can be auto-selected and loaded.
- Updated the Data page default dock layout to include the new merge panel.

## Merge Sessions panel
The new panel lets the user:
- enter a new merged session name
- merge the currently selected sessions into one new session
- automatically load the merged session after creation

## Merge behavior
When merging:
- a new target session folder is created under the current records root
- images are copied into the new session's `images/` folder
- `records.jsonl` is rebuilt for the merged session
- each merged record gets:
  - a new unique `frame_id`
  - updated `image` path
  - `session` set to the new merged session name
  - `merged_from_session`
  - `source_frame_id`
  - `source_image`
  - `merge_index`

## Safety and validation
- requires at least 2 selected sessions
- prevents using an existing session name as the merge target
- prevents merging into one of the source session names
- skips unusable records with missing or invalid images
- cleans up the new folder if merge fails partway through

## Files changed in this patch
- `piTrainer/pages/data_page.py`
- `piTrainer/panels/data/session_list_panel.py`
- `piTrainer/panels/data/merge_sessions_panel.py`
- `piTrainer/services/data/merge_service.py`
- `PATCH_NOTES/PATCH_NOTES_piTrainer_0_3_1.md`

## Verification done
- Python compile check passed on all patched files
- merge service tested with temporary sample sessions and copied images
- Data page wiring checked for the new panel and callbacks

## Notes
This is a patch-only zip. Copy these files over the same relative paths inside your current `piTrainer_0_3_0` project.
