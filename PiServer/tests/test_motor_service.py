from __future__ import annotations

import unittest

from piserver.services.motor_service import MotorService


class MotorServiceTests(unittest.TestCase):
    def test_apply_settings_preserves_last_good_values_for_bad_inputs(self):
        svc = MotorService()
        svc.apply_settings({
            "left_direction": -1,
            "right_direction": 1,
            "steering_direction": -1,
            "left_max_speed": 0.7,
            "right_max_speed": 0.8,
            "left_bias": 0.1,
            "right_bias": -0.1,
        })
        cfg = svc.apply_settings({
            "left_direction": "bad",
            "right_direction": None,
            "steering_direction": "-1",
            "left_max_speed": float("nan"),
            "right_max_speed": "oops",
            "left_bias": float("inf"),
            "right_bias": object(),
        })
        self.assertEqual(cfg["left_direction"], -1)
        self.assertEqual(cfg["right_direction"], 1)
        self.assertEqual(cfg["steering_direction"], -1)
        self.assertAlmostEqual(cfg["left_max_speed"], 0.7)
        self.assertAlmostEqual(cfg["right_max_speed"], 0.8)
        self.assertAlmostEqual(cfg["left_bias"], 0.1)
        self.assertAlmostEqual(cfg["right_bias"], -0.1)

    def test_get_persisted_config_excludes_gpio_runtime_flag(self):
        svc = MotorService()
        cfg = svc.get_persisted_config()
        self.assertNotIn("gpio_available", cfg)

    def test_reverse_throttle_flips_turn_bias(self):
        svc = MotorService()
        left_fwd, right_fwd = svc.update(0.2, 0.6, 1.0)
        left_rev, right_rev = svc.update(0.2, -0.6, 1.0)
        self.assertGreater(right_fwd - left_fwd, 0.0)
        self.assertLess(right_rev - left_rev, 0.0)

    def test_reverse_throttle_respects_reversed_steering_direction(self):
        svc = MotorService()
        svc.apply_settings({"steering_direction": -1})
        left_fwd, right_fwd = svc.update(0.2, 0.6, 1.0)
        left_rev, right_rev = svc.update(0.2, -0.6, 1.0)
        self.assertLess(right_fwd - left_fwd, 0.0)
        self.assertGreater(right_rev - left_rev, 0.0)


if __name__ == "__main__":
    unittest.main()
