# Visual Design Update 1A — VD04–VD07 development checkpoint

Base: ac6f5274247107a7730a075f03bbce540e1c6543 (settings-flood PR #102, stacked on #98). Main 3a2a5756 has additional documentation; retain when integrating. PR #99 1.0.0 has pre-existing failed hardware-free CI 46034291646; do not replay it or promote stable. Existing version markers retained pending qualification and version-line reconciliation.

Scope: theme colours and preference persistence only. No geometry, motor/camera/inference, training data, control ownership or existing settings-flood handler changes. Existing historical baseline screenshots remain pinned. Initial implementation checkpoint, not a release or completed VD04–VD07 acceptance.

Added two presets to existing style dialog; preserved legacy Ops Flat and custom key, separate saved per-preset overrides and inherited layout settings. Preview/cancel and explicit Save selection. Existing default retained when no preference because fresh and legacy installs cannot reliably be distinguished. VM persistence regression added. Remaining: rendered dashboard/dialog contrast audit and exact CI.
