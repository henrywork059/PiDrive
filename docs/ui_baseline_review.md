# Exact visual baseline review — pending explicit owner approval

Exact verified source ba2420536b733659c6cb4796490cdb38f8d31914, Linux [45915971367](https://github.com/henrywork059/PiDrive/actions/runs/45915971367) 4/4 and Windows [45915971393](https://github.com/henrywork059/PiDrive/actions/runs/45915971393) 1/1. Independently verified actual archives PiSD 15161709968 SHA-256 dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3 and PiServer 15162386493 SHA-256 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c. All six matrices, 78/78 cases, 8/8 recording journeys, no case/page errors. 256/256 actual width and height measurements >=44px (PiSD STOP 96, recording 48, dialogs 48; PiServer STOP 16, dialogs 48). Node PiSD responsive 18/18, PiServer responsive 15/15, accessibility 34/34; Windows native 40 tests, Linux trainer passed. Forward dry runs 15/10/11 changed files passed.

Independent 105-PNG comparison to 35be24a: PiSD 83 images, 56 byte-identical, eight full-page dimension increases 15–16px; PiServer 22 images, ten byte-identical, no dimension changes; none missing. Phone and landscape dialog montage independently inspected. Owner review package and manifest prepared, no images saved as approved golden. Manifest SHA-256 407e870465cbfaecd697c9c5890acc51a5fa23f5953b25027cfd87a1e46f13c5. No native Qt screenshot artifact; desktop visual approval separate.

## Review candidate

- Exact source: ba2420536b733659c6cb4796490cdb38f8d31914 on update/three-active-f4-validation.
- Download the two original browser artifacts from the Linux run; verify both SHA-256 digests above. The 105 PNGs are synthetic fixture captures, not physical camera evidence.
- Review actual page hierarchy, preview and STOP availability, recording and session state, settings, presets, focus, phone and short-landscape dialog reachability. Identify objections by exact screenshot path.
- Explicit owner decision must identify the source revision and both archive hashes. Do not automatically promote images or substitute a new revision. If approved, record approval separately and compare subsequent cosmetic candidates against that exact approved set.
- Native desktop visual, screen-reader, physical touch and hardware safety acceptance are not implied by web screenshot approval. Windows and Linux native automated Qt tests passed; no desktop screenshot archive exists for this run.

## Remaining development gates

R35: all existing asserted workflows passed; computed accessibility inventory and findings review still required. UX75: repeatable visual/interaction gates exist and pass; exact baseline owner approval pending. Do not claim 56/56 or 9/9 until justified. Existing candidate markers unchanged. No merge, force push, stable promotion, physical deployment or inactive-component work.
