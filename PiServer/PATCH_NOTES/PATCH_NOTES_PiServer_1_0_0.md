# PiServer 1.0.0 — unified release candidate

Package baseline: 9285733eeb3c392a86ee0615d1e6bcf71eaf08ab
Release transition: 0.4.56 -> 1.0.0

## Request and scope
Owner explicitly requested all three active components transition to 1.0.0 on 2026-11-28, superseding earlier proposed minor versions. This candidate builds on PR #98, not the earlier main or uploaded archive. Its version marker is updated; previous component patch notes and runtime configuration remain unchanged. Historical components are excluded.

## Changes
Version marker and current-version guidance; shared packaging validation supports only the explicit legacy-to-1.0.0 transition and subsequent 1.0.x patches, retaining ancestry, note, path, hash and rollback checks. Emulator display follows PiSD. piTrainer's candidate manifest advertises 1.0.0 without raising the existing minimum or blocking older installations. No motor, camera, data-processing or training algorithm changes are introduced by promotion.

## Verification and limits
Parent corrected CI was still in progress at creation. Release-candidate CI, exact full-package verification, manual visual acceptance and physical P0 checks are pending. Version 1.0.0 is assigned on a draft candidate branch only, not a stable declaration, published tag or deployment. Do not merge or promote until applicable gates pass; retain previous accepted rollback baselines until then.


## Main reconciliation and release regression repair

Reconcile onto qualified main 9285733eeb3c392a86ee0615d1e6bcf71eaf08ab, preserving Update B settings synchronization, previous notes and owner-approved documentation. Exact main regression 46041460253 and emulator 46041460357 passed. Prior release 340be98f failed hardware-free 46034291646: five JS and two Python regression assertions hard-coded the legacy version families, and trainer thread evidence was absent downstream. Update only the version assertions to accept legacy floors or the explicitly authorized 1.0.x family; retain full trainer marker agreement and all safety, accessibility, readback and functional assertions. No runtime change beyond original version candidate, no stable promotion/tag/deployment. Replacement exact CI and release qualification remain required. Concurrent theme PR #103 is not included in this checkpoint; reconcile once its own qualification and source are settled.


## Owner-directed development merge — 2026-11-28

Owner explicitly directed merging all remaining PRs, including the unqualified development candidates. Integrate exact release #99 66efc009e7db1e607265f273b8b0c1cdfbe98a8b and theme #103 680c26ac10e5ec74aae8c1178148a77eabc59047 on previously qualified main 9285733eeb3c392a86ee0615d1e6bcf71eaf08ab. Preserve both histories, all prior notes, Update B, current main docs, config and safety. Shared regression.yml retains release performance gates AND theme tests; package helper retains authorized version transitions AND exact two-SVG allowlist; package tests retain both sets. No release/physical/visual acceptance, stable baseline promotion, tag or deployment. Main development candidate version is 1.0.0. Trainer online manifest latest/allowed 1.0.0 comes from #99, with minimum and blocked versions unchanged.

Known #103 hardware-free failure 46041965199: PiSD job 140651775605 check_vd1a_web.py line 109 fails buttonScale preservation; PiServer job 140651775652 test_accessibility_r35.cjs line 27 fails existing focus contract. Trainer and compatibility jobs passed; browser 46041965195, native Qt 46041965285, trainer visual 46041965189 passed. #99 replacement CI 46042143183, 46042143228, 46042143157 not yet complete; emulator 46042143245, native Qt 46042143147 and visual 46042143387 passed. Do not weaken failing tests or infer complete VD04–VD07 qualification. Exact integrated main CI and follow-up repair are mandatory before release qualification. Owner merge authorization supersedes the earlier no-merge condition only for development integration.
