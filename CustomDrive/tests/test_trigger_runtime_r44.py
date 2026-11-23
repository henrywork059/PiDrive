"""R44 backend trigger mapping regression without hardware/Flask imports.

Extract the *actual source AST* for the U24 trigger math and test it with a
minimal context stub. This deliberately avoids camera, servo, AI and GPIO
initialization while still exercising the committed backend calculations.

Run: cd CustomDrive && python -m unittest tests.test_trigger_runtime_r44 -v
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "custom_drive"
SOURCE = ROOT / "mission1_session_app.py"
DEBUG_TOOLS = ROOT / "debug_tools.py"


def _function(module: ast.Module, name: str, class_name: str | None = None) -> ast.FunctionDef:
    nodes = module.body
    if class_name:
        cls = next(node for node in nodes if isinstance(node, ast.ClassDef) and node.name == class_name)
        nodes = cls.body
    return next(node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name)


def load_trigger_math() -> dict:
    runtime_ast = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    debug_ast = ast.parse(DEBUG_TOOLS.read_text(encoding="utf-8"), filename=str(DEBUG_TOOLS))
    methods = [
        "_trigger_y_px",
        "_pickup_trigger_y_px",
        "_dropoff_trigger_y_px",
        "_capture_deadband_px",
        "_target_close_enough",
    ]
    nodes = [
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        _function(debug_ast, "clamp_float"),
        _function(runtime_ast, "_normalize_ratio_percent_or_fraction"),
        *[_function(runtime_ast, name, "Mission1SessionContext") for name in methods],
    ]
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace: dict = {}
    exec(compile(module, filename=str(SOURCE), mode="exec"), namespace)
    return namespace


class TriggerRuntimeR44(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.impl = load_trigger_math()

    def context(self, grip: float, dropoff: float):
        funcs = self.impl

        class ReadOnlyTriggerContext:
            def __init__(self, values):
                self.values = values

            def _arm_config(self):
                return self.values

        ctx = ReadOnlyTriggerContext({
            "grip_trigger_y_ratio": grip,
            "dropoff_trigger_y_ratio": dropoff,
            "capture_x_tolerance_ratio": 0.05,
        })
        for name in ("_trigger_y_px", "_pickup_trigger_y_px", "_dropoff_trigger_y_px",
                     "_capture_deadband_px", "_target_close_enough"):
            setattr(ReadOnlyTriggerContext, name, funcs[name])
        return ctx

    def test_zero_maps_to_frame_bottom_in_center_origin_coordinates(self):
        ctx = self.context(0, 0)
        self.assertEqual(ctx._pickup_trigger_y_px(360), -180)
        self.assertEqual(ctx._dropoff_trigger_y_px(360), -180)

    def test_fifty_percent_is_exact_frame_center(self):
        ctx = self.context(.5, .5)
        self.assertEqual(ctx._pickup_trigger_y_px(360), 0)
        self.assertEqual(ctx._dropoff_trigger_y_px(360), 0)

    def test_hundred_percent_is_frame_top(self):
        ctx = self.context(1, 1)
        self.assertEqual(ctx._pickup_trigger_y_px(360), 180)
        self.assertEqual(ctx._dropoff_trigger_y_px(360), 180)

    def test_grip_and_dropoff_differ_independently(self):
        ctx = self.context(.2, .8)
        self.assertAlmostEqual(ctx._pickup_trigger_y_px(360), -108)
        self.assertAlmostEqual(ctx._dropoff_trigger_y_px(360), 108)

    def test_normalization_preserves_zero_and_accepts_percent_input(self):
        normalize = self.impl["_normalize_ratio_percent_or_fraction"]
        self.assertEqual(normalize(0, .3, 0, 1), 0)
        self.assertEqual(normalize(50, .3, 0, 1), .5)
        self.assertEqual(normalize(100, .3, 0, 1), 1)

    def test_normalization_clamps_out_of_range(self):
        normalize = self.impl["_normalize_ratio_percent_or_fraction"]
        self.assertEqual(normalize(-40, .3, 0, 1), 0)
        self.assertEqual(normalize(250, .3, 0, 1), 1)
        self.assertEqual(normalize("invalid", .3, 0, 1), .3)

    def test_capture_gate_preserves_original_center_origin_direction(self):
        ctx = self.context(0, 1)
        bottom = ctx._pickup_trigger_y_px(360)
        top = ctx._dropoff_trigger_y_px(360)
        self.assertTrue(ctx._target_close_enough(0, bottom, 640, bottom)[0])
        self.assertFalse(ctx._target_close_enough(0, bottom + 1, 640, bottom)[0])
        self.assertTrue(ctx._target_close_enough(0, 0, 640, top)[0])
        self.assertFalse(ctx._target_close_enough(100, 0, 640, top)[0])

    def test_status_source_and_motion_rates_unchanged_by_ui_markers(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("'grip_trigger_y_ratio': round(_normalize_ratio_percent_or_fraction(", source)
        self.assertIn("'dropoff_trigger_y_ratio': round(_normalize_ratio_percent_or_fraction(", source)
        self.assertIn("'server_status_at_ms': int(time.time() * 1000)", source)
        self.assertIn("sleep_time = max(0.0, tick_s - (time.monotonic() - loop_started))", source)


if __name__ == "__main__":
    unittest.main()
