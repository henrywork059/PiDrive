# VD36 — owner review and integrated visual qualification

## Scope and exact revisions

28 November 2026. Owner requested VD36 and remaining Visual Design qualification after all five development PRs #105–#109 were merged. Immutable integrated main: `7f36b395c4065232712b45932abf74cf0ecd05bf`, tree `0277f7df420c2468c265ce26817cf1ccf8c181e0`. Reconciled #105 head `7b3f74d438682960bb373e3e41ccff97e2c6bddb` has exactly the same Git tree; its run metadata and screenshot manifests retain that head identity. Do not relabel it as a fresh main run. Previous VD1AF `211d5b673b877a7ccc9b0d1330f52f209f13b09e` is historical, not the integrated source. Preserve existing versions, rollback baselines, the ten design decisions and original 56/56 and 9/9 accounting.

**Disposition:** owner-review evidence assembled for the previously qualified changes and the current integrated tree where available. This is a review packet and forward software candidate, **not** final VD34/VD35 acceptance or owner approval. The auxiliary-page candidate and exact new CI must be independently reviewed before finalizing the packet.

## Design decisions and review inventory

All ten owner-approved decisions remain authoritative: Minimalist Professional; Obsidian & Blue; local Inter and IBM Plex Mono; Borderless Workspace; Adaptive Density; Contextual Minimal controls; Adaptive Professional Workspace; Immersive HUD; Task-Adaptive trainer workspace; Dark & Light. See [original plan](PiDrive_Visual_Design_Update_1_Plan.md), [VD1 progress](VD1_PROGRESS.md), [visual evidence](VD1AE_VISUAL_REGRESSION_AUDIT.md), and [functional audit](VD1AF_FUNCTIONAL_REGRESSION_AUDIT.md).

| IDs | Review surface / available evidence | Qualification disposition |
| --- | --- | --- |
| VD01–03 | Historical 105 web PNGs, matching current path inventory, native before/after, documented semantic token roles and approved decisions | Evidence assembled; full individual owner review not yet recorded |
| VD04–07 | PiSD/PiServer/trainer dark/light actual screenshots, local preference and persistence tests; emulator outer appearance independent | Scoped pre-integration tests passed; new auxiliary-page themes candidate |
| VD08–10 | Local Inter/Plex assets, licensed WOFF2/TTF, native font probes, numeric readouts | Scoped evidence retained; complete scale/truncation/manual review open |
| VD11–14 | Local outline icons, action hierarchy, disabled/hover/pressed/focus, input and critical target tests | Scoped candidate passed before integration; new auxiliary controls/keyboard tests pending |
| VD15–17 | Settings/Data hierarchy and adaptive geometry, critical 44px gates | Scoped evidence; full viewport/physical acceptance open |
| VD18–20 | Contextual navigation, status, existing dock/splitter/restore behavior | Scoped tests; integrated auxiliary navigation candidate |
| VD21–23 | Actual camera geometry, Manual/AI HUD, virtual motor STOP/feedback and prediction/applied distinction | Scoped software tests; live hardware/complex image and performance acceptance separate |
| VD24 | PiServer workspace, actual emulator frontend and camera/overlay, virtual-only simulation | Integrated browser evidence available; three auxiliary-page dark/light matrices newly registered |
| VD25–28 | Populated Data/Preprocess, actual CPU training, validation and conversion comparison, distinct repeated exports, charts/tables | Existing qualified synthetic workflow retained; integrated exact new training CI and broader negative cases pending |
| VD29–30 | Existing operational feedback, error/empty/stale and rejected actions | Scoped coverage; no blanket state acceptance |
| VD31–32 | Actual web matrices, Linux/Windows Qt, keyboard, local font/contrast, scoped geometry | Full-size Windows 125% and manual physical DPI, touch, assistive technology remain open |
| VD33 | Cross-component palette and explicit exceptions; independent embedded PiSD | Merged auxiliary pages lacked consistent buttons/textareas, theme controls and workspace links; targeted candidate addresses gap |
| VD34 | Actual before/after and theme screenshots, archive and individual digest checks | Partial; integrated web artifacts, auxiliary matrices and complete individual review required |
| VD35 | Exact functional/compatibility/package/performance suites and negative evidence | Partial; latest exact combined regression/performance and full archives pending |
| VD36 | This owner review ledger, original-resolution image gallery and explicit blockers | Packet prepared; final exact-candidate evidence and owner decision remain open |

Do not infer 36/36 complete from this table. No new visual baseline is selected. An image dimension change alone is not a visual defect; recorded intended changes include hierarchy, spacing, cockpit geometry, theme and native workspace updates. Image decode/hash validation and assembling paired views are not exhaustive manual inspection.

## Independently checked archives

Original approved references: source `ba2420536b733659c6cb4796490cdb38f8d31914`, artifacts 15161709968 and 15162386493, original per-image manifest SHA256 `407e870465cbfaecd697c9c5890acc51a5fa23f5953b25027cfd87a1e46f13c5` from approval record. Both approved archive digests independently matched. Do not replace approved reference images.

In this VD36 review, 17 actual GitHub ZIPs downloaded and read independently; all archive SHA256 values matched GitHub-listed digests and ZIP CRCs passed. All 976 PNGs decoded; 444 declared captures[].sha256 checks matched. Other images have archive integrity and individual newly computed digests, not verified declared capture bindings. Native historical references are separate from approved web reference.

| Artifact | Scope | PNGs | Declared capture hashes | SHA256 |
| --- | --- | ---: | ---: | --- |
| 15161709968 | Approved PiSD | 83 | 0 | dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3 |
| 15162386493 | Approved PiServer | 22 | 0 | 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c |
| 15268493879 | VD1AF PiSD | 165 | 82 | cf3056dbf08683bb2b9a70dd499383adfb06f7ca22d56af38daa84728108abee |
| 15268518649 | VD1AF PiServer | 74 | 48 | c20cbe8eb638754fbfb6e7d56856e0a6b5780c5984fdfcffa1e382aae6d204c8 |
| 15269093262 | VD1AF Windows | 192 | 96 | 7210455fd78ef2d4074b130a8c5bec5bc95c839d88732e155ce39e77db31153a |
| 15268249185 | VD1AF Linux | 93 | 48 | 983d2230be08f2a4da3606ed80e1a29dd8e7dada3f9eb870c568a6206a5eebd6 |
| 15268908750 | VD1AF trained workflow | 6 | 6 | 0f16b24f0bcea02b5a37712e00f7dcbbaf9ef6a5a1a7f0672b3b39671e2be8f5 |
| 15268603482 | VD1AF cockpit | 10 | 10 | 5f95cd0e21faac649cb2eeaf6de0947414a22b5860bd87673a8d068f73dc77e3 |
| 15262705591 | Earlier E03 Linux | 3 | 0 | ab13f625855927cc4fdfd732cccfc6a8d81819320ad33b5fb04c4078ccb917d5 |
| 15262691599 | Earlier E03 Windows | 3 | 0 | e597d209afa8fc5aa88c5c4432446cfb1172066c0b57e858635fcb374d2a2a4d |
| 15260999938 | Earlier scenarios | 12 | 0 | a6cea1bd5c5d19bff7086e98f30e7a9300eda67676383a3fcd76e9332c3e55fc |
| 15269816719 | Integrated-tree Windows | 192 | 96 | a24065338fd154bf71f83a21fb54565a30819f7387d7f4d0ad5d91ea1f710d2a |
| 15269422143 | Integrated-tree Linux | 93 | 48 | 9d646bb4fd6ba912c6b39e24f3c4e8aa8f0c810fc83392465080367dec5dc926 |
| 15269319316 | Integrated-tree scenarios | 12 | 0 | 59d24d6a0300cd8b9895f257132bd02a2e87c0e07a193b88cc61887c6a2864b5 |
| 15269731966 | Integrated-tree Windows observer | 3 | 0 | 7b2cd6d20761a7db76b95b9eb39da63b65eb4fb505481b4c51e5c18bfbfae0fd |
| 15269711888 | Integrated-tree Linux observer | 3 | 0 | 1584523559c8d61ede3d8a347372d8e63f805c9be48caf5b66b4a5aefd0cc989 |
| 15269686633 | Integrated-tree cockpit | 10 | 10 | 426c727b9dc2ed2bd89a2af936725b9ebadfc370f9290b626e9bb5c7b17ec24f |

Artifact downloads: `https://github.com/henrywork059/PiDrive/actions/artifacts/<artifact-id>`; retention is finite, preserve original archives and this audit externally. The independently assembled local owner gallery contains the original PNG bytes, path-paired views and machine-readable per-image audit. It is a review artifact, not an installer, release package or new golden image set.

All 105 approved web PNG paths matched latest VD1AF archives, no missing paths; 43 same dimensions, 62 changed dimensions, none byte-identical. All 72 native before-to-after/dark/light pairs had identical dimensions in Linux offscreen and qualified Windows native-display groups. Native integrated-tree Windows display report: actual 1680x1002 logical work area, DPR1, 96 DPI; full-size 125% blocked by logical work area. Prior RC09 tested 1024x768 at 125% on a different source, not proof for this candidate or physical monitor. No supported mode of at least 1800x1200 was present in the inspected prior VD1AF native report.

## CI and outstanding gates

| Revision | Workflow IDs | State at inspection |
| --- | --- | --- |
| Integrated main | 46160967617, 46160967517, 46160967530 | PASS, emulator scenarios/browser/observer |
| Integrated main | 46160967528 | In progress, hardware-free |
| Same integrated tree PR head | 46160958388, 46160958326, 46160958343, 46160958327, 46160958287 | PASS, scenarios/browser/Windows native/visual/observer |
| Same integrated tree PR head | 46160958398, 46160958455, 46160958475 | In progress, strict/regression/workloads |
| Same integrated tree PR head | 46160958290 | Skipped due historical branch eligibility; not a release package pass |
| VD36 candidate | New exact workflows | Pending; do not claim green until jobs and actual artifacts reviewed |

Preserve prior negative evidence: latest VD1AF strict idle CPU reduction 20.74% vs 25% target, concurrent 12.30%; separate RC06 idle 26.67%, native review peak RSS -14.43% vs cumulative P2 25% target. Prior measured native review parity p95 -1.68%, RSS +0.066% vs pre-visual, identical semantic hashes. No new waiver or new performance claim. Matched browser task p50/p95, physical camera, 30–60 minute sustained thermal/energy, representative model and supervised physical P0 remain outstanding. No stable publication or deployment authorization.

## Scoped integrated visual gap and candidate

Inspected actual earlier and integrated-tree environment-editor and diagnostics screenshot evidence. Current auxiliary pages inherit the dark root palette but use unstyled native gray buttons and textarea backing, lack light-theme selectors and are not linked from the workspace. Earlier VD1AD explicitly deferred these pages. Add reversible page-local appearance, semantic controls, local typography and responsive focus/targets; use cached last successful diagnostics data to redraw chart colors only. No theme-related backend requests, new polling, physical authority, persisted preference, scenario mutations or changed fault commands. Preserve existing workspace theme independence and all user data.

Add exact-revision browser matrix on both existing observer OS jobs: three auxiliary pages, dark/light, 390/768/1440 widths, 18 actual screenshots per OS, computed palette/typography/geometry, focus, disabled action and request-echo checks. Add ordinary workspace links. Expand existing strict/resource/regression/native visual and isolated full-candidate archive eligibility only for this branch, preserving prior predicates, baselines and tests. Review new exact artifacts before claiming closure; no source change to PiSD/PiServer/piTrainer runtime.

## Owner decisions still required

1. Review original-resolution before/after pairs, dark/light and populated trainer/actual emulator evidence; identify any unacceptable intentional changes.
2. Review integrated exact candidate visual and functional evidence including new auxiliary pages, actual browser timing and recorded performance limitations. Do not authorize replacing the historical baseline by default.
3. Record manual screen reader/physical touch and high-DPI checks, supervised Pi P0 hardware safety and sustained target-device performance separately.
4. Authorize merge and eventual stable promotion separately only after applicable gates pass. Candidate 1.0.0 and existing stable rollback baselines remain unchanged.

No additional roadmap development, stable promotion, tag, release or physical deployment in VD36. If CI remains in progress, stop with explicit pending disposition and continue qualification rather than inventing a PASS.
