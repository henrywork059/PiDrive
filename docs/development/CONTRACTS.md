# Interface and data contracts

Maintainer compatibility checklist, grounded in merged source inventory at 8f593778eb461f8515f6c12c5fce936dc64cb301 and existing regression records. It is not a generated OpenAPI specification. Verify request/response schema, authorization and side effects in the actual target route; examples below are route identifiers, not commands to execute against hardware.

## Runtime HTTP surfaces (selected actual routes)

| Concern | PiSD | PiServer |
| --- | --- | --- |
| Status/preflight | GET /api/status; GET /api/preflight | GET /api/status; GET /api/preflight |
| Safety read/rearm | GET /api/safety/status; POST /api/safety/rearm | GET /api/safety/status; POST /api/safety/rearm |
| Settings | GET/POST /api/settings; POST /api/settings/apply | POST /api/config/save; POST /api/config/reload |
| Camera | GET /api/camera/config; POST /api/camera/apply; GET /api/camera/frame.jpg | GET /api/camera/config; POST /api/camera/apply; GET /api/camera/frame.jpg |
| Diagnostics | GET /api/recent-events; GET /api/errors | GET /api/recent-events |
| PiServer-specific | Not interchangeable | POST /api/control; POST /api/system/estop; POST /api/record/toggle |

Source: [PiSD app](../../PiSD/pisd/app.py), [PiServer app](../../PiServer/piserver/app.py). Never infer identical semantics from identical paths. POST can affect physical operation; use hardware-free fixtures or isolated emulator, not a real device for automated contract tests.

### Safety and telemetry invariants

- Access and origin policy applies to mutations; do not loosen it to resolve UI errors. STOP remains immediately actionable under uncertainty; rejected/unconfirmed requests are visibly unverified, never successful by assumption.
- Stale or disconnected inference must not resume motion by fresh-frame arrival alone. Respect explicit rearm, manual lease/watchdog, ownership, motor safety and existing fault latches.
- A requested mode is not verified effective runtime. Distinguish hardware, virtual, fallback and offline/unverified, and do not keep stale telemetry looking live.
- Protect control loops from preview/UI resource changes. Frame freshness, raw capture/recording and display publication are distinct. Verify sequence and timestamp ordering, request release and bounded queues.

## Settings and persistence

Treat all runtime config and trainer layout/cache preferences as user-local data. Preserve existing and unknown supported keys, normalization, recovery backups and safe writes. Validate readback of effective settings, restart persistence and rejection behavior. A failed optional refresh is not a failed acknowledged mutation; an aborted browser request is not proof that a server mutation was cancelled. Review actual read-only timeout and stale-result guards.

## Recording -> trainer compatibility

Read producer `PiSD/pisd/services/recording_metadata.py` and both recorder services together with `piTrainer/piTrainer/services/data/record_loader_service.py`.
- Existing loader recognizes steering keys steering/angle/user-angle variants and throttle keys throttle/user-throttle variants, plus legacy image/path and mode aliases. Source defines exact keys (STEER_KEYS, THROTTLE_KEYS, IMAGE_KEYS, MODE_KEYS). Do not casually remove aliases.
- Preserve label-file precedence, hidden-record identities, image path resolution, source/session/frame identity, overlay and provenance metadata. Generated/mirrored rows must resolve back to the correct source, including duplicate frame IDs across sessions.
- Preserve column order, global type inference, explicit None versus missing values, empty schema index semantics and source-row ordering across JSONL batch sizes. Optimize only with exact parity.
- Edits, Hide/Recover and destructive purge must retain their existing scope and confirmation semantics. Preserve atomic writes and failed-save retry.
- Emulator manifests identify synthetic simulation; do not represent synthetic driving as real sensor/road data. Keep label semantics compatible.

## Model and export compatibility

Inspect the actual `core/model_manifest.py` in both runtimes and trainer export/deployment/manifest helpers. PiSD manifest recognizes steering_control and yolo_detection kinds and steering_throttle and yolo_boxes interpretations; recognition is not support for activating YOLO on steering runtimes. Preserve expected family, dimensions, output mapping/order and SHA-256 verification. Missing/legacy metadata handling must follow existing policy rather than inventing provenance. Experiment sidecar is separate from model manifest; checksum validates model bytes, not truth of claimed training history. Reject incompatible/corrupt artifacts before activation and retain prior valid model.

## Test or change procedure

1. Record old contract and target exact behavior; identify all readers/writers and legacy inputs.
2. Add fixtures for valid, invalid, missing, stale, duplicate and boundary values as relevant.
3. Compare response structure, identity, order, dtype, pixel/label/output semantics, error handling and side effects, not merely success codes.
4. Prefer additive backward-compatible migrations. Explicitly document unavoidable compatibility change with owner approval.
5. Run relevant producer and consumer tests; see [test selection](TESTING.md). Any failure in safety, data or model parity blocks qualification.
