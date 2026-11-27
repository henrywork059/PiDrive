# Integration and release playbook

Operational checklist supplementing [AGENTS.md](../../AGENTS.md), [package policy](../patch_package.md) and [stabilization acceptance](../stabilization_acceptance.md). No new merge, stable or deployment permission is granted by this file.

## Before any change or merge

- Fetch live main, branch HEADs and PR metadata. Record exact SHAs, merge base and pending version allocations. Review current files and latest plus previous three component notes. Preserve unmerged concurrent changes where required by the task.
- Check component boundaries, saved data, launcher paths, security and UI/recording/model contracts. Do not replay a superseded branch just because its PR is open.
- Identify which branch is source of truth for each component/shared CI file. Compare paths and blobs; resolve conflicts with deliberate forward reconciliation, not broad ours/theirs overwrite.
- Maintain original benchmark baseline, approved screenshot archive and historical notes. Documentation-only changes do not allocate component versions.

Read-only Git inspection examples from root (replace placeholders with verified refs):

```sh
git fetch origin
git log --oneline --first-parent origin/main -n 15
git merge-base origin/main CANDIDATE_SHA
git diff --name-status BASE_SHA CANDIDATE_SHA
git diff --check BASE_SHA CANDIDATE_SHA
git merge-base --is-ancestor SOURCE_SHA CANDIDATE_SHA
git rev-parse CANDIDATE_SHA:PiSD
git rev-parse CANDIDATE_SHA:PiServer
git rev-parse CANDIDATE_SHA:piTrainer
```

These are inspection commands, not authorization to modify a branch. Whole-tree identity is strong evidence for unchanged component bytes, not proof of full runtime equivalence when shared files change.

## Candidate version and packaging

| Component | Actual version marker |
| --- | --- |
| PiSD | PiSD/pisd/__init__.py (__version__) |
| PiServer | PiServer/piserver/app.py (APP_VERSION, underscore format) |
| piTrainer | piTrainer/piTrainer/version.py (APP_VERSION and PATCH_VERSION) |

Historical baselines 0.11.0 / 0.4.0 / 0.11.0 respectively unless owner updates them. Merged versions at inspected main 8f593778eb461f8515f6c12c5fce936dc64cb301: 0.11.48 / 0.4.55 / 0.11.34. Pending integration reserves newer versions; do not allocate from this dated snapshot. Emulator has no independent version number.

Use exact full Git SHAs with history and clean disposable baseline worktree:

```sh
python tools/patch_package.py build --component PiSD --base BASE_SHA --target TARGET_SHA --archive PiSD_patch.zip
python tools/patch_package.py dry-run --component PiSD --base BASE_SHA --target TARGET_SHA --archive PiSD_patch.zip
```

Run dry-run in the exact baseline checkout as specified in package policy. Repeat for the appropriate component; dry-run is not extraction, installation or hardware testing. Preserve changed/new-file-only packaging, paths and version/previous-note validation. Never package user configs/recordings/models or credentials. For unchanged components inherited-source qualification must meet implemented exact ancestry and entire tree identity, not a guessed historical version. For changed components use correct own forward baseline.

## Merge/release gates

| State | Required evidence |
| --- | --- |
| Implemented | Actual code and tests present, no rollback in diff |
| Qualified | Applicable exact-SHA CI complete, actual artifacts independently reviewed where required, parity and failures recorded |
| Merged | Owner-authorized merge and confirmed main ancestry; reconcile stale PR records without replay |
| Owner accepted | Explicit scope-specific visual/functional/physical decisions recorded |
| Stable | Separate owner authorization and required release gates including physical P0 |
| Deployed | Actual target installation and supervised validation recorded |

Do not merge stale candidate evidence after main or target source changes without checking impact and exact combined qualification. Re-read latest concurrent PR state before mutation; no force push or unsafe ref replacement. Preserve all prior commits and historical notes. A docs-only change may change Git HEAD without changing runtime source; record both tested code SHA and docs SHA, do not misattribute CI. See [testing](TESTING.md).

## Worked historical lesson

PR #93 corrected trainer DataFrame semantics. #95 carried the new performance note on an older package parent; package verification correctly failed. #97 replayed UI-only changes on the qualified parent. #98 integrated exact trainer 0.11.35 first, then 0.11.36, while retaining PiSD #96 iframe security and allocating a forward UI2 version. Combined CI then found unnamed PiServer navigation headings. This illustrates why branch-local green checks are not enough, why version ordering matters, and why exact combined qualification must remain mandatory. See [error log](../roadmaps/DEVELOPMENT_AND_ERROR_LOG.md) for exact commits and status; do not infer that the historical pending state is current.

## Completion checklist

Review scope/diff, component versions and latest four notes; test persisted settings, safety and data contracts; collect exact CI and artifact evidence; verify changed-file package integrity; list remaining gates and blockers; confirm explicit owner authorization for merge/promotion/deploy separately; write handover. Never convert an unperformed check into PASS.
