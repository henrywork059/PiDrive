# Performance Update 1 — development checkpoint (not release candidate)

Baseline: main 14c57c990ff0f9bae2003e4e8aa552d17a4227c7; hardware-free regression 45986688308, four jobs passed. Latest and previous three versioned notes inspected. No version increment, merge, release or deployment; this is a draft source checkpoint pending exact-revision regression and full milestone completion.

Measured locally on Linux, NumPy 2.3.5 / pandas 2.2.3, synthetic matched operation snippets, five alternating paired rounds, median CPU ms per operation: PiSD normalization 0.1103 -> 0.1059; PiServer normalization 0.0604 -> 0.0593; trainer 10,000 preview rows 182.4487 -> 7.7460. Exact fixture equality checked. These are not full runtime, supported dependency matrix, physical Pi, or energy measurements. No complete live checkout available locally (network DNS blocked); GitHub connector retrieved exact source. Full candidate CI pending. Existing settings, safety and accepted UI baseline must remain intact.

Changed model_service.py (owned float normalization), camera_service.py (only construct needed fallback placeholder), app.js (skip unchanged health text/class), corresponding existing CI regression tests. No capture timing or safety change.

## Continuation

Exact parent 31f2226596e3552aacb4ce745ce72f50ca216af1: Linux 45992157666 four jobs and Windows 45992157641 one job passed. Suppress duplicate MJPEG publication sequence and stopped-stream spin; preserve fresh JPEG format and control paths. Same-dtype tensor conversion avoids redundant copy at interpreter boundary. Added generator and tensor tests. Full new revision CI and benchmark remain pending; no release version, promotion, config or hardware changes.
