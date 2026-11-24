# Active roadmap progress — 2026-11-24

Scope: PiSD, PiServer, piTrainer and PiBooter. Count original proposal IDs once (not PRs or component-specific patches). The 75 original IDs are preserved. Retire 14 exclusive CustomTrainer/CustomDrive IDs: U18, U22, U24, U25; R33, R41, R42, R44; UX66–UX71. Active total: 61.

## Implementation coverage

This is a conservative planning audit based on the four original roadmap documents, merged/pending PR titles, relevant current source, and green integration PR #84 / CI run 45349043534. "Implemented" means a corresponding implementation is present in the candidate and no further active implementation gap was identified in this review; it is not a claim of exhaustive proposal acceptance, physical hardware testing, or merge into main. Partial means specific further work/verification remains. "No dedicated update" means no distinct PR implementing that proposal was identified; overlap from prior work is not counted as completion.

| Track | Active | Implemented | Partial | No dedicated update | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| F1–F10 | 10 | 3 | 3 | 4 | 7 |
| U11–U29 | 15 | 14 | 1 | 0 | 1 |
| R30–R53 | 20 | 11 | 5 | 4 | 9 |
| UX54–UX75 | 16 | 0 | 0 | 16 | 16 |
| Total | 61 | 28 | 9 | 24 | 33 |

Implemented IDs: F1, F5, F6; U11, U12, U13, U14, U15, U16, U17, U19, U20, U23, U26, U27, U28, U29; R30, R31, R32, R34, R37, R38, R39, R40, R43, R46, R47. Evidence: merged PRs #9–42 (active portions), pending PRs #44–79 (active portions), and #81–84. F5 uses the stale-camera timeout contract; F6 uses the passing active regression matrix.

| Partial ID | Remaining work |
| --- | --- |
| F2 | PiSD server-side manual command lease; PiServer watchdog is present. |
| F3 | PiSD access policy; PiServer access control is present. |
| F4 | Both validation scripts imported missing helpers; follow-up patch targets actual production methods. Full standalone command success outstanding. |
| U21 | PiServer autonomous stale-frame enforcement/rearm audit; PiSD guard is present. |
| R35 | Complete active desktop accessibility/input audit. |
| R36 | Complete actual responsive screenshot/interaction acceptance at required widths. |
| R45 | Finish PiSD token/drift audit. |
| R48 | Complete applicable PiBooter passive readiness checks. |
| R49 | Complete PiSD sanitized bounded operator event view. |

No dedicated update: F7–F10 (config recovery, refactoring, dependencies/packaging, full recording/model workflow); R50–R53 (visual/interaction tests, full provenance, modular extraction, release/anti-rollback checks); UX54–UX65, UX72–UX75. Prior CI, contract and provenance work overlaps several of these but is not treated as full completion.

Next: F4 validation recovery, safety gaps F2/F3/U21, config integrity F7, release checks R53/F9, then remaining workflow and UI/UX work. Keep original numbers and update this ledger using evidence after each patch. 33 active proposal IDs remain for implementation, completion or verification; 24 have no dedicated update. No retired-component work. No hardware acceptance claimed.

## Release candidate
PR #84: PiSD 0.11.22, PiServer 0.4.28, piTrainer 0.11.10, PiBooter 0.1.8. CI run 45349043534: all five jobs passed. Main remains unchanged. The F4 follow-up is separately stacked on the green candidate; its CI status must be checked independently.
