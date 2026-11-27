# Visual Design Update 1A — VD04–VD07 development checkpoint

Base: ac6f5274247107a7730a075f03bbce540e1c6543 (settings-flood PR #102, stacked on #98). Main 3a2a5756 has additional documentation; retain when integrating. PR #99 1.0.0 has pre-existing failed hardware-free CI 46034291646; do not replay it or promote stable. Existing version markers retained pending qualification and version-line reconciliation.

Scope: theme colours and preference persistence only. No geometry, motor/camera/inference, training data, control ownership or existing settings-flood handler changes. Existing historical baseline screenshots remain pinned. Initial implementation checkpoint, not a release or completed VD04–VD07 acceptance.

Added shared dark/light role tokens and colour overrides for existing page panels, controls, status, warnings, logs and focus. Existing high contrast and panel presentation storage remain intact; built directly on #102. Token contrast regression added. Remaining: all-page rendered audit, actual backend save/readback/restart and cross-context tests, legacy literal/overlay audit, exact CI. No physical evidence.


Second checkpoint: registered additive token/persistence regressions and actual Chromium / native Qt capture tests in existing CI; no original matrix removed. Added explicit contrast variants and persistence-preserving fixes. CI not yet executed at time of this commit; rendered and release acceptance remain open.
