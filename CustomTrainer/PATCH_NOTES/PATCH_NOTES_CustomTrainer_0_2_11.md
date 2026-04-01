# PATCH NOTES — CustomTrainer 0_2_11

## Request summary
Shrink the Marking tab right-side panel because it takes too much horizontal space and makes the main frame preview too small.

## Root cause
The Marking tab was still using a wide default right-panel splitter width, generous right-panel stretch factors, and a two-column quick-deploy control row with long button labels. Older saved splitter states could also restore an overly wide right panel even after newer layout defaults were introduced.

## Files changed
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`

## Exact behavior changed
- reduced the default Marking right-panel width
- increased the center preview stretch so the frame area gets more horizontal space by default
- added a right-panel maximum width clamp so restored splitter states cannot keep the panel overly wide
- changed the Marking quick-deploy buttons to a stacked vertical layout so the tools panel can stay narrower
- updated the visible app version to `0_2_11`

## Verification performed
- rebuilt forward from the current accepted `0_2_10` patch state
- checked the recent CustomTrainer patch line to avoid rolling back startup, dataset, shortcut, export, and Export Validate changes
- ran `python -m compileall custom_trainer run_custom_trainer.py` successfully

## Known limits / next steps
- the panel width is now capped to keep the preview larger, but users can still resize splitters within the narrower range
- if an even more compact Marking layout is desired, the next step would be turning some right-side groups into collapsible sections or moving part of the status text into the bottom status bar
