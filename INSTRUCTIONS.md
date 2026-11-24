# PiDrive Maintenance & Instruction Guide (Current Snapshot)

This guide defines how to maintain documentation, requirements references, and low-risk repo updates so instructions stay aligned with live code.

## 1) Scope and intent

Active development: PiSD, PiServer, piTrainer and PiBooter only. CustomTrainer and CustomDrive are inactive historical components; do not create, reopen, merge or continue their component-specific updates unless explicitly requested. Preserve existing source and history. Shared active-runtime safety and model-family rejection checks remain in scope.

Use this guide when you are:
- updating instructional documentation
- aligning run/setup commands with current entry points
- syncing requirements references across projects
- adding preventive notes from known bug history

If a change can affect robot motion, model outputs, network behavior, or persisted formats, treat it as a functional change and require targeted testing.

## 2) Canonical entry points

Use these scripts as the source of truth when editing docs:

- `PiSD/PiSD.py`
- `PiServer/server.py`
- `piTrainer/main.py`
- `PiBooter/run_pibooter.py`

## 3) Current version markers (code-derived)

Verify these before publishing release notes or README updates:

- PiServer app version: `PiServer/piserver/app.py`
- PiServer UI layout-key version: `PiServer/piserver/web/static/app.js`
- PiSD version: `PiSD/pisd/__init__.py`
- piTrainer version: `piTrainer/piTrainer/version.py`

Do not assume the latest number from `PATCH_NOTES/` is active unless the corresponding code marker is updated.

## 4) Requirements synchronization policy

For each project (`PiSD`, `PiServer`, `piTrainer`, `PiBooter`):

1. Confirm `requirements.txt` exists.
2. Ensure README install commands reference the correct file path.
3. Keep Python version guidance consistent (prefer 3.11 unless project-specific constraint exists).
4. Clearly separate **Pi-only optional dependencies** (`picamera2`, `RPi.GPIO`, `tflite-runtime`) from core desktop/server dependencies.
5. Avoid undocumented dependency additions.

## 5) Instruction-document update checklist

When updating any instructional doc:

1. Verify every referenced path exists (`rg --files`).
2. Verify each command references real scripts/modules.
3. Ensure “current vs archive” sections explicitly label snapshot folders/zips as non-active.
4. Update version references only from current code constants.
5. Add troubleshooting notes for common failure modes (camera fallback, motor simulation fallback, model disabled behavior).
6. Link to `BUG_PREVENTION_NOTES.md` when bug-prevention guidance is relevant.

## 6) Bug-prevention documentation policy

When patch notes mention a bug/fix that can recur:

- Add a prevention rule in `BUG_PREVENTION_NOTES.md`.
- Include: root cause pattern, affected module, detection checklist, and prevention checklist.
- Prefer actionable guardrails (shape validation, coordinate normalization checks, UI saved-state clamping, version-key bump policy).

## 7) Safe vs unsafe maintenance changes

### Usually safe
- README/INSTRUCTIONS wording and structure improvements
- command/path correction when behavior is unchanged
- clarification of setup prerequisites and environment notes
- adding cross-links among existing docs

### Usually unsafe (requires extra review)
- camera/motor service defaults or control-loop tuning
- inference preprocessing/postprocessing behavior
- route/state-machine sequencing
- API route semantics or payload schema
- runtime config key changes

## 8) Validation expectations for docs-only updates

Minimum checks:
- `git diff -- <doc files>` review for scope accuracy
- command/path sanity check using static inspection

Optional if environment allows:
- `python -m compileall` for touched Python modules (if any)

## 9) Commit and PR conventions

- Use explicit prefixes: `docs:`, `chore:`, `fix:`
- Keep PR scope focused and descriptive
- Include a short “What changed” and “Why”
- Include a checklist of checks actually performed
- If execution checks were intentionally not run, state that clearly

## 10) Archived artifacts handling

Treat these as historical references unless explicitly required:
- `PiServer_0_3_4/`
- `PiServer_0_4_1/`
- root-level timestamped zip snapshots

Do not promote archived folders in quick-start sections.
