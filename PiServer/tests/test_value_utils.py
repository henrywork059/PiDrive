from __future__ import annotations

import unittest

from piserver.core.value_utils import normalize_direction, parse_bool_like, parse_clamped_float


class ValueUtilsTests(unittest.TestCase):
    def test_parse_bool_like_handles_string_inputs(self):
        self.assertTrue(parse_bool_like("true"))
        self.assertTrue(parse_bool_like("ON"))
        self.assertFalse(parse_bool_like("false", True))
        self.assertFalse(parse_bool_like("0", True))
        self.assertTrue(parse_bool_like("unknown", True))

    def test_parse_clamped_float_rejects_non_finite_values(self):
        self.assertEqual(parse_clamped_float(float("nan"), 0.4, 0.0, 1.0), 0.4)
        self.assertEqual(parse_clamped_float(float("inf"), 0.4, 0.0, 1.0), 0.4)
        self.assertEqual(parse_clamped_float(2.0, 0.4, 0.0, 1.0), 1.0)

    def test_normalize_direction_only_returns_signs(self):
        self.assertEqual(normalize_direction(-99), -1)
        self.assertEqual(normalize_direction(0), 1)
        self.assertEqual(normalize_direction("bad", -1), -1)


if __name__ == "__main__":
    unittest.main()
