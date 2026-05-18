#!/usr/bin/env python3
"""Validate the retired Autopilot page compatibility path.

Scripted Autopilot has been replaced by AI Mode. The legacy files are kept only
so old bookmarks/static references redirect to `/ai-mode` instead of running
scripted motor profiles.
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
TEMPLATE = WEB_ROOT / "templates" / "autopilot.html"
CSS = WEB_ROOT / "static" / "css" / "autopilot.css"
JS = WEB_ROOT / "static" / "js" / "autopilot.js"
AI_TEMPLATE = WEB_ROOT / "templates" / "ai_mode.html"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "autopilot_page"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "ok": bool(self.ok), "code": self.code, "message": self.message, "details": dict(self.details)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate retired PiSD Autopilot compatibility page.")
    parser.add_argument("--static-only", action="store_true", help="Skip Flask route/API checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": TEMPLATE, "css": CSS, "js": JS, "ai_template": AI_TEMPLATE}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(Result(
            f"autopilot_compat.file.{name}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        ))
    return results


def check_source_contract() -> Result:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        ai_template = AI_TEMPLATE.read_text(encoding="utf-8")
    except Exception as exc:
        return Result("autopilot_compat.source_contract", False, PiSDErrorCodes.TEST_AI_MODE_FAILED, f"failed to read source: {exc}")

    expected = {
        "template": ["PiSD Autopilot replaced", "url=/ai-mode", "Scripted Autopilot has been replaced", "/ai-mode"],
        "css": ["scripted Autopilot CSS is intentionally retired", "AI Mode: /ai-mode"],
        "js": ["scripted Autopilot JS is retired", "window.location.replace('/ai-mode')"],
        "ai_template": ["PiSD AI Mode", "legacy_autopilot_alias", "old scripted Autopilot page has been replaced"],
    }
    sources = {"template": template, "css": css, "js": js, "ai_template": ai_template}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in expected.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    return Result(
        "autopilot_compat.source_contract",
        not missing,
        PiSDErrorCodes.OK if not missing else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "legacy Autopilot files redirect to AI Mode" if not missing else "legacy Autopilot compatibility source contract missing tokens",
        {"missing": missing},
    )


def check_routes() -> list[Result]:
    try:
        app = create_app(hardware_enabled=False)
    except RuntimeError as exc:
        return [Result("autopilot_compat.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]
    client = app.test_client()
    results: list[Result] = []

    response = client.get("/autopilot")
    ok = response.status_code == 200 and b"PiSD AI Mode" in response.data and b"old scripted Autopilot page has been replaced" in response.data
    results.append(Result(
        "autopilot_compat.route.alias_page",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "/autopilot loads AI Mode compatibility page" if ok else "/autopilot did not load AI Mode compatibility page",
        {"http_status": response.status_code},
    ))

    for path, label, marker in (
        ("/testing/static/css/autopilot.css", "autopilot_compat.static.css", b"intentionally retired"),
        ("/testing/static/js/autopilot.js", "autopilot_compat.static.js", b"/ai-mode"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(Result(label, ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, f"{path} loaded" if ok else f"{path} failed", {"http_status": response.status_code}))
    return results


def main() -> int:
    args = parse_args()
    results = check_files()
    results.append(check_source_contract())
    if not args.static_only:
        results.extend(check_routes())
    for result in results:
        emit(result)
    ok = all(r.ok for r in results)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": ok, "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(output), "code": PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "failed": sum(1 for r in results if not r.ok)}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
