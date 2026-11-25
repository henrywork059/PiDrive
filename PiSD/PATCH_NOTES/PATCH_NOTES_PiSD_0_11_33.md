# PiSD 0.11.33 — Batch 5 / portable manifest contract

Optional validated run metadata in existing model manifest; legacy models remain supported. No inference or motor changes. Cross-component tests exercise renamed artifact transfer and malformed metadata rejection.

Parent b641f02 verified Linux 45554836806 4/4 and Windows 45554836817 1/1. Reviewed actual entry points and latest four notes per component. Manifest schema v1, legacy behavior, family/input/output/checksum checks, launchers and paths retained. Portable run claims are not authenticated. Exact new CI required; no physical or owner acceptance.
