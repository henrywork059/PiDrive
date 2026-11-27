# PiDrive final release-candidate handover — 2026-11-27

## State

Repository: henrywork059/PiDrive. Branch: update/three-active-f4-validation. Exact tested candidate source: bb15dc9b18ddeac58c53e56ea4868800346f04d4. This handover is added in a documentation-only forward commit; verify live branch HEAD and its CI before any later release action.

**56/56 active software proposals and 9/9 batches complete.** Original 75 proposals: 19 retired exclusive proposals, 56 active. F 10/10, U 13/13, R 19/19, UX 14/14. No unfinished active roadmap proposal. Separate release acceptance remains open.

| Component | Candidate | Real launcher | Latest forward-package dry run |
| --- | --- | --- | --- |
| PiSD | 0.11.45 | PiSD/PiSD.py | 0.11.44 → 0.11.45, 15 files |
| PiServer | 0.4.53 | PiServer/server.py | 0.4.52 → 0.4.53, 10 files |
| piTrainer | 0.11.32 | piTrainer/main.py | 0.11.31 → 0.11.32, 11 files |

No new version allocated, no release tag or archive publication. The dry runs above validate patch-package integrity; they are not distributed patch ZIPs or physical installation tests.

## Verified gates

Verified exact candidate bb15dc9b18ddeac58c53e56ea4868800346f04d4, Linux [45921885146](https://github.com/henrywork059/PiDrive/actions/runs/45921885146) 4/4 and Windows [45921885201](https://github.com/henrywork059/PiDrive/actions/runs/45921885201) 1/1. Independent latest artifact downloads: PiSD 15164627462 SHA-256 4f3850f6d2f3428bcebadf25c65f3c2ab9154219f59b4c4f1b809258bd19cddc; PiServer 15163714987 SHA-256 cced837f4169f890dc2ff0d1a18c5838e9067f46a2435628c245b2e5cc32674b. Six exact-revision matrices 78/78 zero case/page errors; 67 inventories/2689 enabled control observations zero findings; 15 atomic AI geometry samples with seven panels and >=10px separation; 256 target measurements >=44px both dimensions. Forward package dry runs 15/10/11 changed files passed. Compared all 105 PNG paths against approved ba24205: no missing or new images; PiSD 62/83 and PiServer 17/22 byte-identical. Two PiSD full-page AI screenshots shorter by 16/17px, no PiServer dimension changes. Selected changed-size comparisons inspected, no production visual/runtime source changes between pinned and candidate: only fixture tools and documentation/notes. Exact approved baseline remains unchanged.

Previous exact 0eb9138 gate passed 4 Linux jobs after retry of a transient upstream apt 403 and 1 Windows job; no security or test bypass. Native Windows eight suites 40 tests; Linux trainer Qt, clean dependency smoke and real TFLite export passed. Existing recording, STOP, access control, config recovery, model compatibility, layout persistence, selection identity and anti-rollback contracts retained.

## Approved web visual reference

Owner explicitly approved the reviewed PiDrive web screenshot baseline on 2026-11-27 (15:41 HKT/Taipei local time), source ba2420536b733659c6cb4796490cdb38f8d31914. Approved original archives: PiSD artifact 15161709968 SHA-256 dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3; PiServer artifact 15162386493 SHA-256 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c. Approved 105 web PNGs only (83 PiSD, 22 PiServer); original per-image manifest SHA-256 407e870465cbfaecd697c9c5890acc51a5fa23f5953b25027cfd87a1e46f13c5. Both original archive digests and manifest rechecked independently. Preserve these exact captures for subsequent visual comparison; do not substitute later screenshots. Archive retention is finite: retain the original review archive and approval record outside CI. Approval does not cover native desktop visual review, screen readers, physical touch/hardware or stable-release promotion.

## Remaining acceptance, not new roadmap proposals

| Gate | State |
| --- | --- |
| Scoped software roadmap and automated CI | Complete at exact tested candidate |
| Web visual baseline | Explicit owner approval recorded |
| Desktop native visual acceptance | Pending; no Qt screenshot archive in this gate |
| Native screen readers, physical touch and arbitrary custom themes | Not fully verified |
| Supervised physical Pi hardware, actual motor/STOP/rearm/camera and device integration | Not performed; separate safety gate |
| Frozen EXE, target-environment installation and real deployment | Not claimed |
| Stable promotion, merge and deployment | Not authorized |

## Next authorized work

Maintain the tested candidate. Obtain separate acceptance for the outstanding physical/native checks before proposing a stable release. For any new patch, read AGENTS.md, current live source, latest plus three preceding notes, and validate exact CI/forward packages. Compare subsequent cosmetic changes against the exact approved web archive set; never silently replace the golden reference. Preserve persistent runtime/config data and component boundaries. Do not merge, force push, promote, deploy, modify inactive components or allocate new versions for documentation alone.

References: [PROGRESS](PROGRESS.md), [schedule](DEVELOPMENT_SCHEDULE.md), [baseline approval](../ui_baseline_review.md), [regression gate](../ui_regression_gate.md), component PATCH_NOTES.
