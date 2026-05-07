# AGENTS.md — PiDrive Codex Instructions

Use these instructions when working on the PiDrive repository with Codex or any automated coding assistant.

PiDrive is an active multi-component engineering monorepo. Treat it as real runtime software, not as a documentation-only repository.

---

## 1. Source of truth priority

When instructions or files conflict, follow this order:

1. Latest explicit user instruction in the current task
2. Remembered project-specific baseline/version rules
3. Latest uploaded relevant component zip or repo zip
4. Actual files and folders currently in the repo
5. Older notes, patch notes, or assumptions

Do not guess paths, entry points, versions, or folder layout. Inspect the repo first.

---

## 2. Repository structure

PiDrive is a monorepo with separate components. Common top-level folders include:

- `PiServer/` — current Pi-side runtime and web control server
- `PiBooter/` — boot-time Wi-Fi onboarding service
- `piTrainer/` — desktop trainer
- `CustomTrainer/` — YOLO-oriented desktop training workflow
- `CustomDrive/` — custom drive/runtime workflow with GUI, headless, and web modes
- `piCar_0_3_2/` — legacy reference/fallback runtime

Do not flatten, rename, reorganize, or merge these folders unless the user explicitly asks.

---

## 3. Component isolation rule

Work on only the component requested.

Examples:

- A `PiServer` task must not modify `PiBooter`, `piTrainer`, `CustomTrainer`, `CustomDrive`, or `piCar_0_3_2` unless explicitly requested.
- A `piTrainer` task must not change `CustomTrainer`, even if the names seem related.
- `piCar_0_3_2/` is legacy reference code. Do not modernize or patch it unless explicitly requested.

If the task is unclear, inspect the repo and choose the smallest likely component scope. Do not perform broad repo rewrites.

---

## 4. Real entry points

Before editing README files, launch instructions, patch notes, setup files, or scripts, verify the real entry points.

Important known entry points include:

- `PiServer/server.py`
- `PiBooter/run_pibooter.py`
- `piTrainer/main.py`
- `CustomTrainer/run_custom_trainer.py`
- `CustomDrive/run_custom_drive_demo.py`
- `CustomDrive/run_custom_drive_gui.py`
- `CustomDrive/run_custom_drive_headless.py`
- `CustomDrive/run_custom_drive_web.py`
- `piCar_0_3_2/server.py`

Do not leave docs pointing to stale launch commands.

---

## 5. Anti-rollback rule

Every patch must build forward from the latest accepted state.

Before finalizing a patch, check:

- Did any file get replaced by an older version?
- Did any recent UI change disappear?
- Did any recent setting stop applying?
- Did any accepted bugfix vanish?
- Did any config key or file path change unexpectedly?
- Did patch notes or version lines regress?

When the user asks to review, update, continue, or create the latest patch, compare against:

1. The latest current code state
2. The latest patch note for that component
3. The previous 3 patch notes for that same component, when available

If a rollback risk is found, fix it before finalizing.

---

## 6. Patch style

Prefer targeted, minimal, reliable edits.

Do:

- Patch only necessary files
- Preserve exact relative paths
- Keep component-specific files inside their component folder
- Preserve existing runtime behavior unless intentionally changing it
- Add clear error handling and logs where useful
- Keep compatibility with existing saved settings
- Update README only when commands or behavior actually changed
- Add patch notes for every delivered patch

Avoid:

- Broad rewrites without need
- UI-only fake fixes
- Replacing full files with older snapshots
- Renaming folders/files casually
- Mixing unrelated component changes into one patch
- Claiming tests were run when they were not

---

## 7. Config and runtime data safety

Treat runtime/config files as persistent user data.

Do not casually wipe, reset, or hardcode over existing values.

Important config paths include, but are not limited to:

- `PiServer/config/`
- `PiBooter/config/`
- `CustomDrive/config/`
- `CustomDrive/config/runtime_settings.json`
- `CustomDrive/config/run_settings.json`

If a schema change is required:

- Preserve existing values where possible
- Add missing keys safely
- Clamp invalid values instead of crashing
- Keep backward compatibility when practical
- Do not delete unknown user-local keys unless the user explicitly asks

---

## 8. Versioning rules

Do not invent a new version scheme.

Known baseline/version rules:

- `PiServer` stable baseline: `PiServer_0_4_0`; future bug-fix patches use `0_4_x`
- `piCar` stable baseline: `piCar_0_3_0`; future patches use `0_3_x`
- `piTrainer` patch zips should contain only changed/updated files and preserve exact structure
- `PiServer` patch zips should follow the uploaded `PiServer` folder/path baseline and include changed/new files plus patch notes inside `PiServer/PATCH_NOTES/`

If a newer stable baseline is given in the current task, follow the newer instruction.

Before choosing the next version number:

1. Inspect the component's `PATCH_NOTES/` folder
2. Check the latest version line in existing notes
3. Follow the user's remembered stable baseline rule
4. Use the next logical patch number only after confirming the above

---

## 9. Packaging rules

For component patch zips:

- Include only changed files, new files, and patch notes unless the user asks for a full copy
- Preserve exact folder structure
- Do not add extra nesting
- Do not include unrelated files
- Keep patch notes inside the component's `PATCH_NOTES/` folder

For full-project work:

- Only package the full repo if the user explicitly asks
- Otherwise prefer a minimal patch package

---

## 10. Patch notes requirements

Every patch zip must include detailed patch notes.

Patch notes must include:

- Request summary
- Cause/root cause if known
- Files changed
- Exact behavior changed
- Verification actually performed
- Known limits or next steps

Do not claim hardware testing, runtime testing, or UI testing unless it was actually performed.

---

## 11. Component rules

### 11.1 PiServer

`PiServer/` is the current main Pi-side runtime and web control server.

Respect:

- `PiServer/server.py`
- `PiServer/config/`
- `PiServer/piserver/`
- `PiServer/piserver/web/`
- `PiServer/PATCH_NOTES/`

Priorities:

- Settings must really apply, not just update UI labels
- Saved settings must survive restart
- UI changes must not break backend runtime logic
- Camera, motor, model, recorder, and control services should remain separated
- Preserve simulation/fallback behavior when Pi-only dependencies are unavailable
- Keep web control responsive and debuggable

Do not break recent layout, style, settings, or runtime fixes.

### 11.2 PiBooter

`PiBooter/` is separate from `PiServer/`.

Respect:

- `PiBooter/run_pibooter.py`
- `PiBooter/config/`
- `PiBooter/pibooter/`
- `PiBooter/boot/`
- `PiBooter/PATCH_NOTES/`

Priorities:

- Keep Wi-Fi onboarding reliable
- Preserve boot/systemd-oriented behavior
- Keep `nmcli` integration explicit and debuggable
- Do not mix PiBooter changes into PiServer unless requested

### 11.3 piTrainer

`piTrainer/` is the desktop trainer.

Respect:

- `piTrainer/main.py`
- `piTrainer/piTrainer/pages/`
- `piTrainer/piTrainer/panels/`
- `piTrainer/piTrainer/services/`
- `piTrainer/PATCH_NOTES/`

Priorities:

- Preserve docking, panel modularity, playback, filtering, shortcuts, and validation improvements
- Preserve Windows usability
- Keep README/setup commands accurate
- Package only changed/updated files for patch zips

### 11.4 CustomTrainer

`CustomTrainer/` is the YOLO-oriented desktop workflow.

Respect:

- `CustomTrainer/run_custom_trainer.py`
- `CustomTrainer/custom_trainer/ui/`
- `CustomTrainer/custom_trainer/services/`
- `CustomTrainer/PATCH_NOTES/`

Priorities:

- Preserve runnable training, validation, prediction, and export flow
- Keep Ultralytics/YOLO helper paths stable
- Prefer robust UI behavior over flashy changes
- Do not break documented launch commands

### 11.5 CustomDrive

`CustomDrive/` is a real runtime project with GUI, headless, demo, and web modes.

Respect:

- `CustomDrive/run_custom_drive_demo.py`
- `CustomDrive/run_custom_drive_gui.py`
- `CustomDrive/run_custom_drive_headless.py`
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/config/`
- `CustomDrive/custom_drive/`
- `CustomDrive/PATCH_NOTES/`

Priorities:

- Keep shared settings behavior
- Preserve GUI/headless/web mode separation
- Keep simulation usable when live dependencies are unavailable
- Do not describe it as placeholder-only if real code exists

### 11.6 Legacy piCar

`piCar_0_3_2/` is a legacy/fallback reference.

Rules:

- Do not patch or modernize it unless explicitly asked
- Do not remove it
- Preserve compatibility
- Use it as a reference only when helpful

---

## 12. Verification expectations

When practical, run lightweight checks before finalizing.

Useful checks include:

```bash
python -m compileall PiServer
python -m compileall PiBooter
python -m compileall piTrainer
python -m compileall CustomTrainer
python -m compileall CustomDrive
```

Use only the check relevant to the component being changed.

Also verify where practical:

- Referenced files exist
- README launch commands match real files
- Config loading handles missing or older keys
- New imports do not break startup
- Patch package contains only intended files

Be honest about checks that could not be performed, especially hardware checks on Raspberry Pi.

---

## 13. Documentation rules

When updating documentation:

- Keep commands copy/paste friendly
- Verify actual launcher paths first
- Include Windows/Linux/macOS commands only when relevant
- Remove stale file references
- Keep each README focused on install, run, config, and known notes
- Do not overstate features that are not wired into runtime code

---

## 14. Good Codex task pattern

Use precise, scoped tasks.

Good example:

```text
Work only inside PiServer/.
Fix runtime settings not applying after restart.
Inspect PiServer/server.py, PiServer/config/, and the latest 3 PiServer patch notes first.
Do not touch PiBooter, piTrainer, CustomTrainer, CustomDrive, or piCar_0_3_2.
Preserve existing runtime.json user values.
Run python -m compileall PiServer.
Summarize changed files and verification.
```

Bad example:

```text
Improve the whole project.
```

---

## 15. Final response expectations

When completing a task, report:

- Component touched
- Files changed
- Behavior changed
- Verification performed
- Package path/name if a zip was created
- Known limits or hardware checks still required

Keep the summary practical and grounded in the actual files.
