# VD1AE — independent visual regression audit (VD34)

Audit target: da118bcc4d5504258eea4c000f346cb8ef3e85e4 (VD1AD), not the subsequent repair commit. Pinned web baseline ba2420536b733659c6cb4796490cdb38f8d31914; native trainer baseline 0f28889459796c6672b0b830c095205c83579e11. Emulator comparison is last green VD1AC 6251d73de09435cd685db963110fa3ea32d8141a, not a retroactively invented original baseline. No baseline replacement or automatic pixel-equality gate.

## Exact CI before edits

46152743272 native Windows success; 46152743289 trainer visual Ubuntu and Windows success; 46152743274 all four regression jobs success. 46152743265 emulator failure, job 141002692928, line 231: expected rgb(49,95,209) on Start PiSD, actual rgb(255,255,255) while disabled. The log proves disabled state, so retain disabled presentation and verify enabled accent offline and disabled fill/text online. Keep all previous runtime, STOP, iframe, authorization, settings-echo and font checks.

## Independently downloaded evidence

The following ZIP bytes were read locally, CRC-tested, PNG inventories decoded/compared, and all available captures[].sha256 entries recomputed. SHA-256 values below are computed archive digests; latest candidate and prior-green archives match GitHub's listed digests. Baseline archives contain no captures[].sha256 entries in their matrices; archive hashes recorded without claiming per-image manifest verification.

| Artifact ID | Role | PNG count | Manifest hashes matched | SHA-256 |
|---|---|---:|---:|---|
| 15161709968 | Pinned PiSD | 83 | none provided | dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3 |
| 15162386493 | Pinned PiServer | 22 | none provided | 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c |
| 15266386807 | VD1AD PiSD | 165 | 82 | 7f6cce5c53be55a557f85dd4eb70b66522629506822d2e792a36d9074210bb2f |
| 15266386657 | VD1AD PiServer | 74 | 48 | d55de4c414fe9b7e3b8366ea13a7304392c5e48afd61286fab96f09640985b67 |
| 15266198841 | VD1AD Linux trainer | 93 | 48 | 7bfd47194f8a5ef08c8bb1ef084b2428561813313df15b4e730415912b039e9d |
| 15267055060 | VD1AD Windows trainer | 192 | 96 | fb5485e000470628c8b3a92b95d4bc810a210a79af9727e7dd610bcf425c241a |
| 15266203870 | VD1AD failed emulator | 2 | 2 | 6a4cf4adca9941f1b6c3669ecc469a60f8d92c1369df42a4c54e2050da183e7c |
| 15264805921 | VD1AC emulator reference | 2 | 2 | f9e9c49c2e21b157437d6425849bde516ce664835b1caf1dd3c5c9279567ffe1 |
| 15265394583 | VD1AD trained workflow | 6 | none provided in captures array | c4e1bb169ef144c8205b2419292fc7b34527058282f26029252c37896496adb9 |

All nine CRC checks clean, 276/276 manifest hashes match (including 2 from reference emulator). Also downloaded and verified CRC and archive digests of last green PiSD 15263968172, PiServer 15264855755, Ubuntu 15264387361, Windows 15263798480. Those are intermediate reference, not substitution for VD1AD.

## Paired comparisons and observed findings

- All 105 pinned web PNG filenames present in VD1AD at same relative paths. Decoded and compared pixel equality without resizing: PiSD 31 same-sized changed, 52 different-size; PiServer 12 same-sized changed, 10 different-size; zero pixel-identical. Full-page heights and intended design differences explain some changes; these counts do not classify regressions. Reviewed representative before/after and desktop/mobile contact sheets, not an exhaustive pixel-level manual approval of all 105 pairs. Reviewed latest PiSD light page contact sheet and PiServer light page contact sheet, previous matched PiServer dashboard desktop/mobile and dialog, and emulator before/after live-cockpit/after-stop views. Remaining dark/portrait and full-resolution per-page inspection is outstanding.
- PiSD: exact 48 cockpit cases, both themes, four viewport sizes and three synthetic scenes: max image/overlay coordinate or dimension discrepancy 0px, no page errors. Found actual pale lavender list text on white in vd1a/motor_tuning-light-390.png (also visible desktop). Source motor_tuning.css hardcodes #c7d2fe; curated theme CSS did not map the list. Repair with existing --vd-text in curated themes only; new actual list contrast assertion >=4.5. No motor tuning workflow added or restored.
- PiServer: 24 cockpit cases both themes, four viewports, max overlay alignment error 0.6649305555555429px, no page errors. Representative dashboard and light dialogs preserve structure; disconnected synthetic preview is not live-camera qualification. No confirmed PiServer visual defect in reviewed samples.
- piTrainer: matched all 12 baseline capture filenames against after/dark/light, equal image dimensions in Linux offscreen and qualified Windows native-display groups (36 pairs each). Inspected native dark and light contact sheets across all six stages at 1024/1440. Windows report explicitly qualified actual 1680x1002 work area, DPR1/96dpi, restored mode result 0; 48/48 requested geometry in native-display captures vs 0/48 in initial undersized desktop captures. 125% original-size visual qualification remains blocked by logical work area, despite successful separate simulated keyboard tests. Linux offscreen is not physical display evidence. Native baseline visual sheet and full-resolution individual pairs still need manual review; no new confirmed native regression in inspected samples.
- Emulator: two VD1AC/VD1AD matched live-cockpit and after-stop screenshots inspected; outer dark palette changed intentionally, actual embedded frontend retained. Failed VD1AD archive has only two images; no completed light screenshot or full multi-size visual matrix, no manifest evidence of successful new theme roundtrip. Repair real offline enabled/online disabled assertion, add six actual outer offline screenshots (dark/light x 390/768/1440), retain existing live theme captures and safety/geometry assertions. New gate must run, and actual new screenshots must be audited. Concurrent scenario/diagnostics/environment pages remain on separate PRs and outside these captures.

## Qualification blockers

VD34 remains partial. Exact repair CI and screenshot reinspection needed, including light emulator, full-resolution review of outstanding matched web/trainer captures, 125% native requested-size matrix, physical DPI/screen-reader, live hardware and concurrent emulator scenario pages. Do not infer visual acceptance from successful CI. No baseline change, merge, version, configuration or safety/runtime handler changes. This audit did not locally run the new application code.
