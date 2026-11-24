# PiServer 0.4.32 — Batch 3 / F9 dependency packaging

## Request and root cause
Dependency declarations and test-only requirements diverged; hardware-specific or heavy dependencies need explicit install groups. Core Flask/NumPy/OpenCV constraints aligned with the green hardware-free matrix; optional GPIO and development dependency files; documented OS camera and optional TFLite backend. Existing server.py launcher unchanged.

## Files and baseline
Component README, requirements files and existing version marker only. Direct parent d2020825a6521269c008a6c53720e2adfffa5ea2 adds shared R53 package tooling. Reviewed actual launcher, dependency-bearing modules and latest four component notes (0.4.31/30/29/28) at 8c979f3. No user settings, recordings, models, runtime/control algorithms, UI behavior or inactive trees changed. Shared CI adds fresh-environment install/import smoke checks without removing existing regression tests.

## Verification and limits
Source inspection and prior four-job regression evidence 45359079601; exact new candidate CI and actual forward archive tests required. Clean dependency imports are not physical hardware, full browser, native Windows, real model training or deployment acceptance. Raspberry Pi OS camera/GPIO compatibility and interpreter availability must be checked on the actual device. No production release or runtime merge authorized.
