# PiBooter integration regression corrections (0.1.8)

Initial PR #84 run (45342315514) passed config, provisioning security, onboarding and recent events tests but two older tests required obsolete exact versions. tests/test_ui_copy_r46.py and tests/test_responsive_r36.cjs now enforce the same 0.1.x series and original minimum patch. Other assertions unchanged. Based on integrated 0.1.8; reviewed 0.1.8, 0.1.7, 0.1.6, 0.1.5 notes. No runtime, network, security, config or version changes. Corrected tests require rerun; physical Wi-Fi not tested.
