# piTrainer 0.11.11 — Batch 2 / UX74 destructive-action protection

## Request and behavior
Permanent hidden purge names root, exact sessions and distinct hidden frame/metadata counts; previews source identities and signatures, refuses stale scope, guards reentrant dialog. Existing soft hide/recover and source selection behavior unchanged. Changed visibility mixin, delete service, version and atomicity regression cases.

## Baseline and rollback audit
Direct parent adf44de4ea76067e2165717ad3acd1303c286bcb, CI 45358221582 passed all four jobs. Reviewed current implementation and latest plus previous three component notes (0.11.10/9/8/7). No persisted config, recording, model, layout or retired-component files modified. Existing endpoints retain exact paths, and authorized STOP is not confirmation-gated. Existing external model-delete/reset callers must now send confirm:true where applicable.

## Verification and limits
New hardware-free tests are included in regression CI; exact-commit results pending. No actual user files deleted. Browser helper tests use simulated DOM; real browser and Windows verification remain separate. Confirmations prevent accidental repeated UI submission, not a distributed idempotency protocol. Trainer metadata checks are optimistic and per-file, not a multi-file transaction. No physical hardware acceptance.
