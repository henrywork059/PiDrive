# Visual Design Update 1A — VD04–VD07 development checkpoint

Base: ac6f5274247107a7730a075f03bbce540e1c6543 (settings-flood PR #102, stacked on #98). Main 3a2a5756 has additional documentation; retain when integrating. PR #99 1.0.0 has pre-existing failed hardware-free CI 46034291646; do not replay it or promote stable. Existing version markers retained pending qualification and version-line reconciliation.

Scope: theme colours and preference persistence only. No geometry, motor/camera/inference, training data, control ownership or existing settings-flood handler changes. Existing historical baseline screenshots remain pinned. Initial implementation checkpoint, not a release or completed VD04–VD07 acceptance.

Updated central dark palette, added light palette, startup selection and Appearance menu with explicit next-launch application. Isolated QSettings key, no automatic restart or loss of in-memory work. All six workflow stages and chart token consumers retained. Preference and stylesheet unit regression added. Remaining: native Windows/Linux rendered screenshots, per-widget contrast audit and exact CI.


Second checkpoint: registered additive token/persistence regressions and actual Chromium / native Qt capture tests in existing CI; no original matrix removed. Added explicit contrast variants and persistence-preserving fixes. CI not yet executed at time of this commit; rendered and release acceptance remain open.

- First candidate CI identified the exact light checkbox SVG as a forbidden package change. Extend the reviewed static-asset allowlist only to that exact file, exercise both approved SVGs in the package regression, and preserve arbitrary SVG and all existing blocked-path rejections. Qualification remains pending.
