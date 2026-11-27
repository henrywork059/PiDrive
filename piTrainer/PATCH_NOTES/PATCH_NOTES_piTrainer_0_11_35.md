# piTrainer 0.11.35 — Performance Update 2.5 review memory candidate

Package baseline: 77b3fe8d6a76200caa7f96149c7d7c4bc66cb396
Original performance comparison baseline: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7

PRs #88/#89 were already merged externally. Main contains qualified ba05d2a and only additional roadmap documentation. New draft branch from exact main. Latest four notes 0.11.34/33/32/31 reviewed; 0.11.35 absent from main and open emulator PR #90. No stable promotion.

Parent strict trainer artifact 15211044318 SHA256 7a7280b375cd60a9f40a4e38401a872d60206aee0ccf4241bff33e5ab596bc5d: original peak RSS 361074688→317960192 bytes, p95 86.896→13.306ms, CPU 6.094→3.081s, 15/15 semantic parity. Resource 15211444385 SHA256 4b966ab28ae3353ada9ca11dd7143d6a04bcd7b545675b3e0475f6fa648d342b: prior metadata preparation CPU 92.518→84.284ms, process peak RSS 172355584→172261376 bytes (negligible). 25% whole-review RSS target open.

## Changes
- services/data/plot_service.py, panels/data/data_plot_panel.py: isolated four-column plot snapshot, full review metadata remains in source. Missing/duplicate column fallback, session filter, order, numeric coercion, summary and all six plot types retained. Avoid redundant index-reset copies.
- panels/data/preview_panel.py: one full owning copy followed by index assignment rather than two data copies.
- tests/test_plot_projection_p2.py: all plot artist/summary parity, session filters, nulls, duplicate indexes, copy-on-write modes and unusual schemas.
- version.py: provisional 0.11.35 marker.

Local five-pair synthetic 24k-row 34-column snapshot+all-session filter: CPU 3.765→1.034ms, traced peak 18.687→1.471MiB (COW off); COW on CPU .912→.724ms, peak 12.460→1.471MiB. Exact projected value equality; pandas 2.2.3/NumPy 2.3.5. Isolated equivalent operations, not native Qt or whole-review RSS. CI pending. No cache, recording, label, configuration, random augmentation or safety changes.
