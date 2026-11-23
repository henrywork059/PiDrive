"""R45 stdlib-only smoke checks of piTrainer's accepted UI token contract.

Uses the real Python AST. No PySide6, TensorFlow or GUI initialization.
Run: cd piTrainer && python -m unittest discover -s tests -p 'test_ui_style_contract_r45.py' -v
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "piTrainer" / "ui"
GUIDE = ROOT / "DOCS" / "FORMAT_AND_STYLE_GUIDE.md"


def source_tree(name: str) -> ast.Module:
    path = UI / name
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def assigned_expr(tree: ast.Module, name: str) -> ast.expr:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return node.value
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return node.value
    raise AssertionError(f"Central token {name} not found")


def density_values() -> dict[str, dict[str, object]]:
    definition = assigned_expr(source_tree("formatting.py"), "DENSITY_PROFILES")
    assert isinstance(definition, ast.Dict)
    result = {}
    for key, call in zip(definition.keys, definition.values):
        assert isinstance(call, ast.Call)
        result[ast.literal_eval(key)] = {
            keyword.arg: ast.literal_eval(keyword.value) for keyword in call.keywords
        }
    return result


def stylesheet_template() -> str:
    tree = source_tree("styles.py")
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_stylesheet")
    for node in fn.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "css" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("CSS template is no longer in central stylesheet")


class UiStyleContractR45(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.formatting = source_tree("formatting.py")
        cls.style = source_tree("styles.py")
        cls.theme = source_tree("theme.py")
        cls.profiles = density_values()
        cls.colors = ast.literal_eval(assigned_expr(cls.theme, "THEME_COLORS"))
        cls.roles = ast.literal_eval(assigned_expr(cls.formatting, "BUTTON_ROLES"))
        cls.template = stylesheet_template()
        cls.guide = GUIDE.read_text(encoding="utf-8")

    def test_three_named_density_profiles(self):
        self.assertEqual(set(self.profiles), {"compact", "comfortable", "spacious"})

    def test_density_button_and_input_sizes_increase_monotonically(self):
        for key in ("base_font", "button_min", "input_min", "workflow_tab_min", "banner_title"):
            values = [self.profiles[p][key] for p in ("compact", "comfortable", "spacious")]
            self.assertEqual(values, sorted(values), key)

    def test_density_panel_spacing_and_scrollbar_are_positive(self):
        for name, profile in self.profiles.items():
            with self.subTest(profile=name):
                for key in ("page_spacing", "panel_spacing", "form_h_spacing",
                            "form_v_spacing", "scrollbar", "splitter_handle_width"):
                    self.assertGreater(profile[key], 0)

    def test_comfortable_spacing_matches_documented_contract(self):
        comfortable = self.profiles["comfortable"]
        self.assertEqual(comfortable["page_spacing"], 7)
        self.assertEqual(comfortable["panel_spacing"], 6)
        self.assertEqual(comfortable["form_h_spacing"], 9)
        self.assertEqual(comfortable["form_v_spacing"], 6)

    def test_main_width_thresholds_are_central(self):
        text = (UI / "formatting.py").read_text(encoding="utf-8")
        self.assertIn("if width < 1180:", text)
        self.assertIn("if width > 1680:", text)
        self.assertIn('return "comfortable"', text)

    def test_all_semantic_status_colors_have_entries(self):
        names = {"bg_app", "bg_panel", "text_primary", "text_muted", "info",
                 "success", "warning", "danger", "selection", "border",
                 "text_on_warning"}
        self.assertTrue(names.issubset(self.colors), names - set(self.colors))
        self.assertTrue(all(re.fullmatch(r"#[0-9a-fA-F]{6}", value)
                            for value in self.colors.values()))

    def test_primary_prerequisite_and_destructive_roles_centralized(self):
        expected = {"primary", "secondary", "amber", "danger", "nextStep"}
        self.assertEqual(self.roles, expected)
        for role in expected:
            self.assertIn(f"QPushButton[role='{role}']", self.template)

    def test_role_color_semantics_not_reversed(self):
        self.assertIn("QPushButton[role='primary'] {\n        background: @COLOR_SUCCESS@", self.template)
        self.assertIn("QPushButton[role='amber'] {\n        background: @COLOR_WARNING@", self.template)
        self.assertIn("QPushButton[role='danger'] {\n        background: @COLOR_DANGER@", self.template)

    def test_css_has_no_unresolved_unknown_placeholders(self):
        tokens = set(re.findall(r"@([A-Z][A-Z0-9_]*)@", self.template))
        known = {f"COLOR_{name.upper()}" for name in self.colors}
        known.update({"BASE_FONT", "BANNER_TITLE", "BUTTON_MIN", "NEXT_MIN",
                      "INPUT_MIN", "MAIN_TAB_MIN", "WORKFLOW_TAB_MIN", "SCROLLBAR"})
        self.assertTrue(tokens, "Source stylesheet tokens disappeared")
        self.assertFalse(tokens - known, "Unknown CSS tokens: " + str(tokens - known))

    def test_all_theme_colors_use_theme_lookup(self):
        code = (UI / "theme.py").read_text(encoding="utf-8")
        self.assertIn("return THEME_COLORS.get(name, default)", code)
        self.assertIn("THEME_COLORS", (UI / "formatting.py").read_text(encoding="utf-8"))

    def test_default_widget_roles_are_not_overwritten(self):
        code = (UI / "formatting.py").read_text(encoding="utf-8")
        self.assertIn('if not role:', code)
        self.assertIn('button.setProperty("role", "secondary")', code)
        self.assertIn('button.property("role") == "nextStep"', code)

    def test_resizable_splitter_presets_are_central(self):
        presets = assigned_expr(self.formatting, "SPLITTER_PRESETS")
        self.assertIsInstance(presets, ast.Dict)
        names = {ast.literal_eval(key) for key in presets.keys}
        self.assertIn("three_panel_workspace", names)
        self.assertIn("validation_three_panel_workspace", names)

    def test_style_guide_keeps_semantic_color_and_label_policy(self):
        for text in ("ui/formatting.py", "ui/styles.py", "ui/theme.py",
                     "nextStep", "primary", "secondary", "amber", "danger",
                     "Load Selected", "Start Training", "Run Validation"):
            with self.subTest(token=text):
                self.assertIn(text, self.guide)

    def test_icon_guidance_does_not_force_existing_widget_resize(self):
        for text in ("16 px", "18 px", "20 px", "No global icon-size token",
                     "Do not resize existing toolbar"):
            self.assertIn(text, self.guide)

    def test_version_is_forward_and_version_gate_code_not_duplicated(self):
        version = (ROOT / "piTrainer" / "version.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION = "0.11.8"', version)
        self.assertIn('PATCH_VERSION = "piTrainer_0_11_8"', version)
        self.assertIn("version_gate", self.guide)


if __name__ == "__main__":
    unittest.main()
