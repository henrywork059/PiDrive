#!/usr/bin/env python3
"""Validate PiSD unified page/panel presentation contracts.

This is a static and optional Flask-route check for the shared visual recovery
layer added after the 0.3.1 layout regression. It does not start hardware or
move motors.
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
UNIFIED_CSS = WEB_ROOT / "static" / "css" / "unified_layout.css"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "ui_presentation_consistency"
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

REQUIRED_CSS_TOKENS = [
    "PiSD 0.3.2 unified visual recovery layer",
    ".st-topbar",
    ".mdrv-topbar",
    ".topbar",
    ".md-topbar",
    ".pp-topbar",
    ".pt-hero",
    ".mdrv-shell",
    "grid-template-areas",
    "\"status drive\"",
    "#settingsPanelPresentationPanel",
    ".layout > .card:nth-of-type(1)",
    ".md-panel-preview",
    ".pp-shell",
    ".pt-shell",
    "@media (max-width: 900px)",
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
    parser = argparse.ArgumentParser(description="Validate unified PiSD page/panel presentation.")
    parser.add_argument("--hardware", action="store_true", help="Create Flask app with hardware mode requested. No hardware commands are sent.")
    parser.add_argument("--static-only", action="store_true", help="Only check files/source; skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    files = {"unified_css": UNIFIED_CSS, **TEMPLATES}
    for label, path in files.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(
            Result(
                f"ui_presentation.file.{label}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_UI_PRESENTATION_CONSISTENCY_FAILED,
                f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
                {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
            )
        )
    return results


def check_source_contract() -> Result:
    try:
        css = UNIFIED_CSS.read_text(encoding="utf-8")
        template_sources = {name: path.read_text(encoding="utf-8") for name, path in TEMPLATES.items()}
    except Exception as exc:
        return Result(
            "ui_presentation.source_contract",
            False,
            PiSDErrorCodes.TEST_UI_PRESENTATION_CONSISTENCY_FAILED,
            f"failed to read UI files: {exc}",
            {"exception_type": type(exc).__name__},
        )

    missing_css = [token for token in REQUIRED_CSS_TOKENS if token not in css]
    missing_links = [name for name, source in template_sources.items() if "css/unified_layout.css" not in source]
    ok = not missing_css and not missing_links
    return Result(
        "ui_presentation.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_UI_PRESENTATION_CONSISTENCY_FAILED,
        "all GUI pages include the unified layout layer and required layout decisions" if ok else "unified presentation contract failed",
        {"missing_css": missing_css, "missing_links": missing_links},
    )


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("ui_presentation.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]

    client = app.test_client()
    results: list[Result] = []
    for path, label, marker in (
        ("/", "route.front", b"css/unified_layout.css"),
        ("/manual-drive", "route.manual_drive", b"manualDriveStatusPanel"),
        ("/settings", "route.settings", b"settingsPanelPresentationPanel"),
        ("/testing", "route.testing", b"Settings and API call tester"),
        ("/dashboard", "route.dashboard", b"panel-camera-preview"),
        ("/panel-presentation", "route.panel_presentation", b"panelPresentationControls"),
        ("/panel-testing", "route.panel_testing", b"ptPanelGrid"),
        ("/testing/static/css/unified_layout.css", "static.unified_css", b"PiSD 0.3.2 unified visual recovery layer"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(
            Result(
                f"ui_presentation.{label}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_UI_PRESENTATION_CONSISTENCY_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )
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

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "ok": all(result.ok for result in results),
        "code": PiSDErrorCodes.OK if all(result.ok for result in results) else PiSDErrorCodes.TEST_UI_PRESENTATION_CONSISTENCY_FAILED,
        "results": [result.as_dict() for result in results],
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
