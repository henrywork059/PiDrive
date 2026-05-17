#!/usr/bin/env python3
"""Validate PiSD 0.3.7 responsive layout contracts.

This test is static by default and does not start camera or move motors. It
checks that every GUI page loads the shared layout system last and that the
Manual Drive page keeps the safety-critical semantic order.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
TEMPLATE_DIR = WEB_ROOT / "templates"
LAYOUT_CSS = WEB_ROOT / "static" / "css" / "pisd_layout_system.css"
DESIGN_CSS = WEB_ROOT / "static" / "css" / "pisd_design_system.css"
UNIFIED_CSS = WEB_ROOT / "static" / "css" / "unified_layout.css"
PRESENTATION_REGISTRY = PROJECT_ROOT / "pisd" / "core" / "presentation_registry.py"
GLOBAL_JS = WEB_ROOT / "static" / "js" / "panel_presentation_global.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "responsive_layout_contract"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"

TEMPLATES = {
    "front_page": TEMPLATE_DIR / "front_page.html",
    "manual_drive": TEMPLATE_DIR / "manual_drive.html",
    "settings": TEMPLATE_DIR / "settings_tab.html",
    "testing": TEMPLATE_DIR / "testing_server.html",
    "dashboard": TEMPLATE_DIR / "main_dashboard.html",
    "panel_presentation": TEMPLATE_DIR / "panel_presentation.html",
    "panel_testing": TEMPLATE_DIR / "panel_testing.html",
}

REQUIRED_LAYOUT_TOKENS = [
    "PiSD Responsive Layout System 0.3.7",
    "body.manual-drive-page .mdrv-shell",
    '"status status"',
    '"preview drive"',
    '"preview stop"',
    '"log log"',
    "@media (max-width: 1099px)",
    "@media (max-width: 759px)",
    "body.settings-page .st-grid",
    "body.testing-page .layout",
    "body.dashboard-page .md-shell",
    "body.panel-presentation-page .pp-shell",
    "body.panel-testing-page .pt-shell",
]

REQUIRED_REGISTRY_TOKENS = [
    "css/pisd_layout_system.css",
    "strict-responsive",
    "semanticLayoutLock",
    "status status",
    "preview drive",
    "STYLE_DEVELOPMENT_RULES",
]

REQUIRED_GLOBAL_JS_TOKENS = [
    "layoutSystem",
    "semanticLayoutLock",
    "pisdLayoutSystem",
    "pisdSemanticLayoutLock",
    "previewPriority",
    "topbarMode",
]


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "ok": bool(self.ok),
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate PiSD responsive layout contracts.")
    parser.add_argument("--hardware", action="store_true", help="Create Flask app in hardware mode. No hardware commands are sent.")
    parser.add_argument("--static-only", action="store_true", help="Only check source files; skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    files = {"layout_css": LAYOUT_CSS, "design_css": DESIGN_CSS, "unified_css": UNIFIED_CSS, "presentation_registry": PRESENTATION_REGISTRY, "global_js": GLOBAL_JS, **TEMPLATES}
    results: list[Result] = []
    for label, path in files.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(Result(
            f"responsive_layout.file.{label}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        ))
    return results


def check_source_contract() -> Result:
    try:
        layout_css = LAYOUT_CSS.read_text(encoding="utf-8")
        registry = PRESENTATION_REGISTRY.read_text(encoding="utf-8")
        global_js = GLOBAL_JS.read_text(encoding="utf-8")
        templates = {name: path.read_text(encoding="utf-8") for name, path in TEMPLATES.items()}
    except Exception as exc:
        return Result("responsive_layout.source_contract", False, PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED, f"failed to read layout files: {exc}", {"exception_type": type(exc).__name__})

    missing_layout = [token for token in REQUIRED_LAYOUT_TOKENS if token not in layout_css]
    missing_registry = [token for token in REQUIRED_REGISTRY_TOKENS if token not in registry]
    missing_global_js = [token for token in REQUIRED_GLOBAL_JS_TOKENS if token not in global_js]

    missing_links = []
    wrong_order = []
    missing_body_class = []
    expected_body = {
        "front_page": 'body class="front-page"',
        "manual_drive": 'body class="manual-drive-page"',
        "settings": 'body class="settings-page"',
        "testing": 'body class="testing-page"',
        "dashboard": 'body class="dashboard-page"',
        "panel_presentation": 'body class="panel-presentation-page"',
        "panel_testing": 'body class="panel-testing-page"',
    }
    for name, source in templates.items():
        if "css/pisd_layout_system.css" not in source:
            missing_links.append(name)
        order = [source.find(token) for token in ("css/unified_layout.css", "css/pisd_design_system.css", "css/pisd_layout_system.css")]
        if any(pos < 0 for pos in order) or not (order[0] < order[1] < order[2]):
            wrong_order.append(name)
        if expected_body[name] not in source:
            missing_body_class.append(name)

    manual = templates["manual_drive"]
    manual_positions = [manual.find(token) for token in ("manualDriveStatusPanel", "manualDriveCameraPanel", "manualDrivePadPanel", "manualDriveStopPanel", "manualDriveLogPanel")]
    manual_order_ok = all(pos >= 0 for pos in manual_positions) and manual_positions == sorted(manual_positions)

    ok = not any([missing_layout, missing_registry, missing_global_js, missing_links, wrong_order, missing_body_class]) and manual_order_ok
    return Result(
        "responsive_layout.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED,
        "shared responsive layout contract passed" if ok else "shared responsive layout contract failed",
        {
            "missing_layout_tokens": missing_layout,
            "missing_registry_tokens": missing_registry,
            "missing_global_js_tokens": missing_global_js,
            "missing_layout_links": missing_links,
            "wrong_css_order": wrong_order,
            "missing_body_class": missing_body_class,
            "manual_dom_order_ok": manual_order_ok,
            "manual_positions": manual_positions,
        },
    )


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("responsive_layout.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]
    client = app.test_client()
    checks = [
        ("/", "route.front", b"css/pisd_layout_system.css", b"front-page"),
        ("/manual-drive", "route.manual_drive", b"manualDriveStatusPanel", b"css/pisd_layout_system.css"),
        ("/settings", "route.settings", b"settingsPanelPresentationPanel", b"css/pisd_layout_system.css"),
        ("/testing", "route.testing", b"Settings and API call tester", b"css/pisd_layout_system.css"),
        ("/dashboard", "route.dashboard", b"panel-camera-preview", b"css/pisd_layout_system.css"),
        ("/panel-presentation", "route.panel_presentation", b"panelPresentationControls", b"css/pisd_layout_system.css"),
        ("/panel-testing", "route.panel_testing", b"ptPanelGrid", b"css/pisd_layout_system.css"),
        ("/testing/static/css/pisd_layout_system.css", "static.layout_css", b"PiSD Responsive Layout System 0.3.7", b"status status"),
        ("/api/presentation/manifest", "api.presentation_manifest", b"css/pisd_layout_system.css", b"strict-responsive"),
    ]
    results: list[Result] = []
    for path, label, marker_a, marker_b in checks:
        response = client.get(path)
        ok = response.status_code == 200 and marker_a in response.data and marker_b in response.data
        results.append(Result(
            f"responsive_layout.{label}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED,
            f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
            {"http_status": response.status_code, "bytes": len(response.data)},
        ))
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.append(check_source_contract())
    if not args.static_only:
        results.extend(check_routes(args.hardware))
    for result in results:
        emit(result)
    ok = all(result.ok for result in results)
    summary = {
        "ok": ok,
        "code": PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_RESPONSIVE_LAYOUT_CONTRACT_FAILED,
        "results": [result.as_dict() for result in results],
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
