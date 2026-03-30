from __future__ import annotations

import unittest

from piserver.tools.camera_diagnostic import build_tint_test_cases


class CameraDiagnosticTests(unittest.TestCase):
    def test_build_tint_test_cases_includes_expected_core_cases(self):
        cases = build_tint_test_cases(
            {"format": "BGR888", "auto_white_balance": True},
            include_format_sweep=False,
            include_manual_gain_sweep=False,
        )
        names = [case["name"] for case in cases]
        self.assertEqual(names[:4], [
            "baseline_runtime",
            "force_awb_on",
            "force_awb_off",
            "awb_on_low_saturation",
        ])

    def test_build_tint_test_cases_adds_manual_gain_cases(self):
        cases = build_tint_test_cases(
            {"format": "BGR888"},
            include_format_sweep=False,
            include_manual_gain_sweep=True,
        )
        names = [case["name"] for case in cases]
        self.assertIn("awb_off_rg075_bg115", names)
        self.assertIn("awb_off_rg060_bg130", names)
        manual_case = next(case for case in cases if case["name"] == "awb_off_rg070_bg120")
        self.assertEqual(manual_case["settings"]["auto_white_balance"], False)
        self.assertAlmostEqual(manual_case["settings"]["color_gain_red"], 0.70)
        self.assertAlmostEqual(manual_case["settings"]["color_gain_blue"], 1.20)

    def test_build_tint_test_cases_adds_format_sweep_without_duplicates(self):
        cases = build_tint_test_cases(
            {"format": "BGR888"},
            include_format_sweep=True,
            include_manual_gain_sweep=False,
        )
        names = [case["name"] for case in cases]
        self.assertIn("format_bgr888_awb_on", names)
        self.assertIn("format_rgb888_awb_on", names)
        self.assertIn("format_xbgr8888_awb_on", names)
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
