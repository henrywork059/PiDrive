# piTrainer 0.11.19 — Batch 4/5 accessibility, readiness and validation provenance candidate

## Scope and root cause
Continue from verified 8aabfef (CI 45518657406, four jobs passed). Validation controls lacked explicit accessible names; TFLite Use Latest treated an empty path as the current directory and accepted a directory as a model. Validation results did not retain the run association, and the current model path could misleadingly refer to a remembered external file. The six-tab workflow had no compact input readiness feedback.

## Changes
- Validation and TFLite configuration panels: name active controls, fix latest-file selection to accept real .tflite files only.
- Validation pages and services: capture selected dataset and in-memory identity or checksum-bound experiment association in the result; missing or changed associations remain Unknown; show run ID, association and hash in summary. No model or prediction algorithm changes.
- MainWindow: advisory input icons/tooltips on the existing six tabs; preserve exact order and tab labels, shortcuts and task guards. Inputs available does not mean trained, validated, or deployed.
- Tests: native Qt controls and file picker helper; mixed on-disk current PiSD / PiServer / legacy recording load, label edit, hidden exclusion, mirrored steering, source-disjoint split, non-overwriting dummy export, manifest and experiment linkage/tamper checks. Register both in existing CI.
- Version marker only, no settings schema change.

## Verification and limits
Read live main launcher, latest four trainer notes 0.11.18/17/16/15, current source, current recorder formats, canonical roadmap and CI. Exact new CI required. Dummy bytes are not real trained models; no actual training, hardware or owner visual acceptance. Browser and Windows acceptance and broader Batch 4/5 gates remain open. No proposal count increment.

## Additional acceptance checks
- Native Qt test exercises actual readiness renderer with a six-tab fixture; correct missing-input tooltips. Added separate hosted Windows native-platform workflow requiring the Windows Qt plugin and selected existing interaction tests without skips. This is not owner-device visual acceptance.
- Shared Chromium fixture exercises PiServer Training folder selection during a held GET and confirmed exact-target deletion followed by old GET, using intercepted synthetic acknowledgements and actual DOM at four existing widths. No PiServer runtime change or version bump.
- All new CI results pending.
