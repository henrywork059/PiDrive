#!/usr/bin/env python3
"""Validate PiSD front page and tab navigation.

This checks the compact mode-selection front page, settings/testing/dashboard tabs, panel presentation settings page, and Back to Front Page links. It never starts camera output or moves motors.
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
FRONT_TEMPLATE = WEB_ROOT / "templates" / "front_page.html"
FRONT_CSS = WEB_ROOT / "static" / "css" / "front_page.css"
FRONT_JS = WEB_ROOT / "static" / "js" / "front_page.js"
SETTINGS_TEMPLATE = WEB_ROOT / "templates" / "settings_tab.html"
SETTINGS_CSS = WEB_ROOT / "static" / "css" / "settings_tab.css"
SETTINGS_JS = WEB_ROOT / "static" / "js" / "settings_tab.js"
MAIN_TEMPLATE = WEB_ROOT / "templates" / "main_dashboard.html"
TESTING_TEMPLATE = WEB_ROOT / "templates" / "testing_server.html"
PANEL_TEMPLATE = WEB_ROOT / "templates" / "panel_testing.html"
PRESENTATION_TEMPLATE = WEB_ROOT / "templates" / "panel_presentation.html"
PRESENTATION_CSS = WEB_ROOT / "static" / "css" / "panel_presentation.css"
PRESENTATION_JS = WEB_ROOT / "static" / "js" / "panel_presentation.js"
PRESENTATION_GLOBAL_CSS = WEB_ROOT / "static" / "css" / "panel_presentation_global.css"
PRESENTATION_GLOBAL_JS = WEB_ROOT / "static" / "js" / "panel_presentation_global.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "front_page_tabs"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


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
    parser = argparse.ArgumentParser(description="Validate PiSD front page and tab navigation.")
    parser.add_argument("--hardware", action="store_true", help="Create app in hardware mode. No movement commands are sent.")
    parser.add_argument("--static-only", action="store_true", help="Only check source files, skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    files = {
        "front_template": FRONT_TEMPLATE,
        "front_css": FRONT_CSS,
        "front_js": FRONT_JS,
        "settings_template": SETTINGS_TEMPLATE,
        "settings_css": SETTINGS_CSS,
        "settings_js": SETTINGS_JS,
    }
    results: list[Result] = []
    for name, path in files.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(
            Result(
                f"front_page.file.{name}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
                f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
                {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
            )
        )
    return results


def check_source_contract() -> list[Result]:
    results: list[Result] = []
    try:
        front = FRONT_TEMPLATE.read_text(encoding="utf-8")
        front_css = FRONT_CSS.read_text(encoding="utf-8")
        front_js = FRONT_JS.read_text(encoding="utf-8")
        settings = SETTINGS_TEMPLATE.read_text(encoding="utf-8")
        settings_css = SETTINGS_CSS.read_text(encoding="utf-8")
        settings_js = SETTINGS_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return [Result("front_page.source_contract", False, PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED, f"failed to read files: {exc}")]

    expected = {
        "front_template": [
            "PiSD Front Page",
            "frontPageShell",
            "frontModeSettings",
            "frontModeTesting",
            "href=\"/settings\"",
            "href=\"/testing\"",
            "href=\"/dashboard\"",
            "href=\"/panel-testing\"",
            "frontPageInitialStatus",
        ],
        "front_css": [".fp-shell", ".fp-mode-grid", ".fp-mode-card", "@media (max-width: 760px)"],
        "front_js": ["frontApi", "/api/status", "/api/control/stop"],
        "settings_template": [
            "PiSD Settings Tab",
            "Back to Front Page",
            "settingsSystemPanel",
            "settingsCameraPanel",
            "settingsMotorPanel",
            "stCameraForm",
            "stMotorForm",
            "settingsInitialStatus",
        ],
        "settings_css": [".st-grid", ".st-card", ".st-form-grid", "@media (max-width: 900px)"],
        "settings_js": ["settingsApi", "/api/camera/apply", "/api/motor/apply", "/api/control/stop"],
    }
    sources = {
        "front_template": front,
        "front_css": front_css,
        "front_js": front_js,
        "settings_template": settings,
        "settings_css": settings_css,
        "settings_js": settings_js,
    }
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in expected.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    ok = not missing
    results.append(
        Result(
            "front_page.source_contract",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
            "front/settings source contains required route, mode, API, and style contracts" if ok else "front/settings source contract failed",
            {"missing": missing},
        )
    )

    back_link_sources = {
        "settings": settings,
        "dashboard": MAIN_TEMPLATE.read_text(encoding="utf-8"),
        "testing": TESTING_TEMPLATE.read_text(encoding="utf-8"),
        "panel_testing": PANEL_TEMPLATE.read_text(encoding="utf-8"),
        "panel_presentation": PRESENTATION_TEMPLATE.read_text(encoding="utf-8"),
    }
    missing_back = [name for name, text in back_link_sources.items() if "Back to Front Page" not in text or 'href="/"' not in text]
    ok = not missing_back
    results.append(
        Result(
            "front_page.back_links",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
            "all tabs include Back to Front Page" if ok else "one or more tabs missing Back to Front Page link",
            {"missing_back_link": missing_back},
        )
    )
    return results


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("front_page.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]
    client = app.test_client()
    route_checks = [
        ("/", "front_page.route.root", b"PiSD Front Page", b"frontModeSettings"),
        ("/settings", "front_page.route.settings", b"PiSD Settings Tab", b"Back to Front Page"),
        ("/testing", "front_page.route.testing", b"PiSD Testing Server GUI", b"Back to Front Page"),
        ("/dashboard", "front_page.route.dashboard", b"PiSD Main Dashboard", b"Back to Front Page"),
        ("/panel-presentation", "front_page.route.panel_presentation", b"PiSD Panel Presentation Settings", b"Back to Front Page"),
        ("/panel-testing", "front_page.route.panel_testing", b"PiSD Panel Testing Lab", b"Back to Front Page"),
    ]
    results: list[Result] = []
    for path, label, marker_a, marker_b in route_checks:
        response = client.get(path)
        ok = response.status_code == 200 and marker_a in response.data and marker_b in response.data
        results.append(
            Result(
                label,
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing markers",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )
    for path, label, marker in (
        ("/testing/static/css/front_page.css", "front_page.static.front_css", b".fp-mode-grid"),
        ("/testing/static/js/front_page.js", "front_page.static.front_js", b"frontApi"),
        ("/testing/static/css/settings_tab.css", "front_page.static.settings_css", b".st-grid"),
        ("/testing/static/js/settings_tab.js", "front_page.static.settings_js", b"settingsApi"),
        ("/testing/static/css/panel_presentation_global.css", "front_page.static.presentation_global_css", b"--pisd-ui-gap"),
        ("/testing/static/js/panel_presentation_global.js", "front_page.static.presentation_global_js", b"PiSDPanelPresentation"),
        ("/testing/static/css/panel_presentation.css", "front_page.static.presentation_css", b".pp-shell"),
        ("/testing/static/js/panel_presentation.js", "front_page.static.presentation_js", b"ppSave"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(
            Result(
                label,
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.extend(check_source_contract())
    if not args.static_only:
        results.extend(check_routes(args.hardware))

    for result in results:
        emit(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(output_path), "code": PiSDErrorCodes.OK if all(r.ok for r in results) else PiSDErrorCodes.TEST_FRONT_PAGE_CONTRACT_FAILED, "failed": sum(1 for r in results if not r.ok)}, indent=2))
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
