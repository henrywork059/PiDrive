# Debugging runbook

Use this runbook to isolate failures, not to automatically apply fixes. Source and incident references verified against the repository at 8f593778eb461f8515f6c12c5fce936dc64cb301. Start with [development/error log](../roadmaps/DEVELOPMENT_AND_ERROR_LOG.md) and [bug prevention](../../BUG_PREVENTION_NOTES.md).

## Triage procedure

1. Record component, exact SHA/version, OS, adapter/runtime mode, reproduction, expected vs actual, recent related changes and log/CI IDs. Redact tokens, private paths and user recording/model contents before sharing.
2. If safety or hardware is uncertain, stop controlled testing; do not attempt repeated driving commands, bypass access or reset latches. Use the separate supervised physical procedure.
3. Reproduce on the same candidate in disposable state or native CI. Separate actual application defect, incorrect fixture, dependency/environment fault, packaging mismatch and evidence-quality issue.
4. Find the first failure and trace it to the owning layer. Add a focused test that fails for the original behavior; fix minimal source and re-run affected and combined gates. Do not delete assertions to obtain green CI.

## Diagnostic decision table

| Symptom | Inspect first | Expected diagnostic or preventive action |
| --- | --- | --- |
| UI loads, camera/telemetry offline | Actual status/preflight, access logs, camera service, request trace | Distinguish requested/effective mode, stale frame vs network failure; read-only recovery and STOP uncertainty remain truthful |
| STOP acknowledgement absent | Access, request outcome, safety latch and actuator status | Report unconfirmed; physical STOP separate; no assumed success/rearm |
| Settings save looks successful but restart reverts | Route payload, settings/config store, normalized value, file write and effective readback | Test atomic write, restart, unknown keys and error recovery; never erase user's config |
| Browser status freezes | In-flight GET, timeout, snapshot revision and poll cleanup | Check read-only deadline and stale response rejection; never infer cancelled server POST |
| Blank/clipped dashboard or keyboard jump fails | Actual browser console/AX tree and layout | Check computed name including tabindex=-1, intrinsic row sizing, modal reachability and focus restore at all required widths |
| Emulator page refused but direct PiSD works | Controller origin/port, CSP frame-ancestors, normal frame-denial behavior | Exact selected loopback permission only; test alternate-port rejection and restart generation. Do not disable frame/access security |
| Emulator modifies ordinary settings | Workspace, injected factory arguments and normal settings path | Use disposable explicit workspace; assert ordinary data stays unchanged |
| Trainer labels/filter differ after optimization | Loader aliases, source precedence, identity, dtype, column order | Reproduce mixed/missing/empty data at batch 1/7/512 and compare exact schema/values/order |
| Validation selects wrong image | Source/session/frame identity, generated/mirrored mapping, unloaded session reload | Use duplicate frame IDs in distinct sessions, real navigation, source edit round trip |
| Trainer layout restore differs | Actual Qt geometry and QSettings, deferred resize order | Test restored feasible full ratios, minimums, narrow fallback and restart using disposable settings |
| Model refused or unexpected output | Artifact checksum, manifest family/input shape and output mapping | Fail closed on incompatibility; validate using known safe model, no synthetic physical actuation |
| CI package historical-note error | Declared baseline, first-parent history, full tree identity | Correct ancestry and preserve bytes; do not rewrite history or weaken guard |
| Native Windows screenshot unreadable | Actual PNGs, Qt platform, font preflight and realized window geometry | Reject visual evidence even if CI passes; rerun actual native capture |
| Performance metric misses target | Same baseline/fixture, trial counts, semantic digest, CPU/RSS trade-offs | Report misses separately from regression failure; no cherry-picked replacement or default switch |

## Emulator-based debugging

Use a disposable environment with PiSD dependencies, from root:

```sh
python PiSD_Emulator/run_emulator.py --workspace ./local_emulator_workspace --open-browser
```

Controller defaults to 127.0.0.1:8760; PiSD default local port 5050. Start via the controller; use a fresh workspace directory outside tracked data, never real-device data. Inspect actual PiSD page, virtual outputs, camera, STOP and restart. Do not treat simulation as physical acceptance. See [README](../../PiSD_Emulator/README.md) for current limitations and launcher options.

## Close an incident

Document symptom, observed root cause (or hypothesis), exact failing run/test, source diff, exact corrected run, regression added, evidence and remaining risk. Keep historical failure visible even after fix. Append a new entry to [development/error log](../roadmaps/DEVELOPMENT_AND_ERROR_LOG.md) and relevant component PATCH_NOTES if source changed. Classify fixed-but-unqualified separately from verified fixed.
