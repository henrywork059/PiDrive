# PATCH NOTES — piTrainer_0_3_11

## Fixed
- **Path Preview** now renders as an actual curved trajectory instead of reading like a straight line.
- **Record Preview** no longer stops at 50 frames; it now shows all loaded frames.

## Details
### 1) Curved Path Preview
The previous path preview used one cubic path from the bottom center to a single end point. In practice that often looked too straight and did not feel like a projected driving path.

This patch changes the drawing logic to build the path step-by-step by integrating heading changes over small segments. That makes the overlay bend progressively left or right as steering increases, so it reads more like a future path.

### 2) All frames in preview
The preview table was capped at 50 rows in `preview_service.py`.

This patch removes that cap by default so the table can show the full filtered dataset instead of only the first 50 frames.

## Changed files
- `piTrainer/services/data/overlay_service.py`
- `piTrainer/services/data/preview_service.py`

## Verification
- Python compile check passed on the patched files.
- Patch zip includes only changed files plus patch notes.
- Patch zip keeps the same wrapper-folder style and relative paths.
