# Visual Design Update 1D — typography and adaptive layout

Base: 46ac66bdc96948c80aee25173078aaf3e9c143e4. Exact parent 46ac66bdc96948c80aee25173078aaf3e9c143e4 passed hardware-free 46105411989, emulator 46105411971, Windows native Qt 46105411995 and trainer visual 46105411994. Main stability workflows 46105154184 and 46105154155 passed separately.

Request: typography, control consistency and adaptive layout. Local TTF (879708 + 173052 bytes); module-relative registration and native fallback preserving size, technical editor mono, launcher and onedir inclusion. Native glyph/fallback and evidence tests. Preserve training/export/workspace and density behavior.

Files: component-local fonts with notices and provenance; ui/typography.py, app.py, ui/styles.py, PACKAGING/piTrainer_onedir.spec and tests/test_theme_vd04_vd07.py. Shared browser/native evidence and exact-path binary package checks updated. Upstream and destination Git blob identities and asset byte counts verified. No external runtime font requests, changed config, safety or versions; previous patch notes and approved baseline preserved. Candidate CI and rendered inspection pending. No stable promotion, deployment or requirement acceptance.
