"""Regression for the restored AI validation entrypoints and real runtime math."""
import unittest

from scripts.ai_validation_math import correction_case, safety_case
from scripts.test_ai_mode_page import check_correction_math
from scripts.run_standard_validation import _check_ai_helper_math


class AIValidationMathTests(unittest.TestCase):
    def test_ai_page_math_checks(self):
        results = check_correction_math()
        self.assertEqual(len(results), 4)
        for result in results:
            with self.subTest(label=result.label):
                self.assertTrue(result.ok, result.as_dict())

    def test_standard_math_check(self):
        result = _check_ai_helper_math()
        self.assertTrue(result.ok, result.as_dict())

    def test_expired_or_disabled_correction_does_not_modify_model_output(self):
        for enabled, age in ((True, 0.76), (False, 0.1)):
            with self.subTest(enabled=enabled, age=age):
                result = correction_case(0.4, -0.2, -0.6, 0.4,
                                         gain_percent=50, age_s=age, enabled=enabled)
                self.assertFalse(result["manual_active"])
                self.assertAlmostEqual(result["steering"], 0.4)
                self.assertAlmostEqual(result["throttle"], -0.2)

    def test_limiter_clamps_without_reversing_steering(self):
        result = safety_case(0.9, -0.8, {
            "output_mode": "steering_and_throttle", "max_steering": 0.5,
            "max_throttle": 0.3, "steering_smoothing": 0,
            "throttle_smoothing": 0,
        }, {"steering": 0, "throttle": 0})
        self.assertAlmostEqual(result["steering"], 0.5)
        self.assertAlmostEqual(result["throttle"], -0.3)


if __name__ == "__main__":
    unittest.main()
