# PiSD 0.11.28 — Batch 3 / F9 dependency packaging

## Request and root cause
Dependency declarations and test-only requirements diverged; hardware-specific or heavy dependencies need explicit install groups. Core simulation dependencies separated from optional GPIO and developer tools; singular requirement.txt is a compatibility alias, not a second inconsistent scaffold. Removed stale unzip-over-checkout guidance. Actual PiSD.py launcher and token requirement retained.

## Files and baseline
Component README, requirements files and existing version marker only. Direct parent d2020825a6521269c008a6c53720e2adfffa5ea2 adds shared R53 package tooling. Reviewed actual launcher, dependency-bearing modules and latest four component notes (0.11.27/26/25/24) at 8c979f3. No user settings, recordings, models, runtime/control algorithms, UI behavior or inactive trees changed. Shared CI adds fresh-environment install/import smoke checks without removing existing regression tests.

## Verification and limits
Source inspection and prior four-job regression evidence 45359079601; exact new candidate CI and actual forward archive tests required. Clean dependency imports are not physical hardware, full browser, native Windows, real model training or deployment acceptance. Raspberry Pi OS camera/GPIO compatibility and interpreter availability must be checked on the actual device. No production release or runtime merge authorized.
